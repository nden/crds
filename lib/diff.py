"""This module differences two CRDS reference or mapping files on the local
system.   It supports specification of the files using only the basenames or
a full path.   Currently it operates on mapping, FITS, or text files.
"""
import os
import sys

from crds import rmap, log, pysh, cmdline, utils

from pyfits import FITSDiff

# ============================================================================
        
def mapping_diffs(file1, file2):
    """Return the logical differences between CRDS mappings named `file1` 
    and `file2`.
    """
    assert rmap.is_mapping(file1), \
        "File " + repr(file1) + " is not a CRDS mapping."
    assert rmap.is_mapping(file2), \
        "File " + repr(file2) + " is not a CRDS mapping."
    assert os.path.splitext(file1)[-1] == os.path.splitext(file2)[-1], \
        "Files " + repr(file1) + " and " + repr(file2) + \
        " are not the same kind of CRDS mapping:  .pmap, .imap, .rmap"
    map1 = rmap.fetch_mapping(file1, ignore_checksum=True)
    map2 = rmap.fetch_mapping(file2, ignore_checksum=True)
    differences = map1.difference(map2)
    return differences

def diff_action(diff):
    """Return 'add', 'replace', or 'delete' based on action represented by
    difference tuple `d`.   Append "_rule" if the change is a Selector.
    """
    if "replace" in diff[-1]:
        result = "replace"
    elif "add" in diff[-1]:
        result = "add"
    elif "delete" in diff[-1]:
        result = "delete"
    elif "different classes" in diff[-1]:
        result = "class_difference"
    elif "different parameter" in diff[-1]:
        result = "parkey_difference"
    else:
        raise ValueError("Bad difference action: "  + repr(diff))
    if "Selector" in diff[-1]:
        result += "_rule"
    return result

def mapping_difference(observatory, file1, file2, primitive_diffs=False, check_diffs=False,
                       mapping_text_diffs=False):
    """Print the logical differences between CRDS mappings named `file1` 
    and `file2`.  
    
    IFF primitive_differences,  recursively difference any replaced files found
    in the top level logical differences.
    
    IFF check_diffs, issue warnings about critical differences.   See
    mapping_check_diffs().
    """
    differences = mapping_diffs(file1, file2)
    if mapping_text_diffs:   # only banner when there's two kinds to differentiate
        log.write("="*20, "logical differences",  repr(file1), "vs.", repr(file2), "="*20)
    for diff in differences:
        diff = unquote_diff(diff)
        if primitive_diffs:
            log.write("="*80)
        log.write(diff)
        if primitive_diffs:
            if "replaced" in diff[-1]:
                old, new = diff_replace_old_new(diff)
                difference(observatory, old, new, primitive_diffs=primitive_diffs)
    if mapping_text_diffs:
        for (d1, d2) in mapping_pairs(differences):
            log.write("="*20, "text difference", repr(d1), "vs.", repr(d2), "="*20)
            text_difference(observatory, d1, d2)
        log.write("="*80)
    if check_diffs:
        mapping_check_diffs_core(differences)

def mapping_pairs(differences):
    """Return the sorted list of all mapping tuples found in differences."""
    pairs = set()
    for diff in differences:
        for pair in diff:
            if len(pair) == 2 and rmap.is_mapping(pair[0]):
                pairs.add(pair)
    return sorted(pairs)
        
def unquote_diff(diff):
    """Remove repr str quoting in `diff` tuple."""
    return diff[:-1] + (diff[-1].replace("'",""),)

def unquote(name):
    """Remove string quotes from simple `name` repr."""
    return name.replace("'","").replace('"','')

def diff_replace_old_new(diff):
    """Return the (old, new) filenames from difference tuple `diff`."""
    _replaced, old, _with, new = diff[-1].split()
    return unquote(old), unquote(new)

def diff_added_new(diff):
    """Return the (old, new) filenames from difference tuple `diff`."""
    _added, new = diff[-1].split()
    return unquote(new)
    
# ============================================================================

def mapping_check_diffs(mapping, derived_from):
    """Issue warnings for *deletions* in self relative to parent derived_from
    mapping.  Issue warnings for *reversions*,  defined as replacements which
    where the replacement is older than the original,  as defined by the names.   
    
    This is intended to check for missing modes and for inadvertent reversions
    to earlier versions of files.   For speed and simplicity,  file time order
    is currently determined by the names themselves,  not file contents, file
    system,  or database info.
    """
    mapping = rmap.asmapping(mapping, cached="readonly")
    derived_from = rmap.asmapping(derived_from, cached="readonly")
    log.info("Checking derivation diffs from", repr(derived_from.basename), "to", repr(mapping.basename))
    diffs = derived_from.difference(mapping)
    mapping_check_diffs_core(diffs)

def mapping_check_diffs_core(diffs):
    """Perform the core difference checks on difference tuples `diffs`."""
    categorized = sorted([ (diff_action(d), d) for d in diffs ])
    for action, msg in categorized:
        if action == "add":
            log.verbose("In", _diff_tail(msg)[:-1], msg[-1])
        elif "rule" in action:
            log.warning("Rule change at", _diff_tail(msg)[:-1], msg[-1])
        elif action == "replace":
            old_val, new_val = map(os.path.basename, diff_replace_old_new(msg))
            if newer(new_val, old_val):
                log.verbose("In", _diff_tail(msg)[:-1], msg[-1])
            else:
                log.warning("Reversion at", _diff_tail(msg)[:-1], msg[-1])
        elif action == "delete":
            log.warning("Deletion at", _diff_tail(msg)[:-1], msg[-1])
        elif action == "parkey_difference":
            log.warning("Different lookup parameters", _diff_tail(msg)[:-1], msg[-1])
        elif action == "class_difference":
            log.warning("Different classes at", _diff_tail(msg)[:-1], msg[-1])
        else:
            raise ValueError("Unexpected difference action:", action)

def _diff_tail(msg):
    """`msg` is an arbitrary length difference "path",  which could
    be coming from any part of the mapping hierarchy and ending in any kind of 
    selector tree.   The last item is always the change message: add, replace, 
    delete <blah>.  The next to last should always be a selector key of some kind.  
    Back up from there to find the first mapping tuple.
    """
    tail = []
    for part in msg[::-1]:
        if isinstance(part, tuple) and len(part) == 2 and isinstance(part[0], str) and part[0].endswith("map"):
            tail.append(part[1])
            break
        else:
            tail.append(part)
    return tuple(reversed(tail))

# =============================================================================================================

def newstyle_name(name):
    """Return True IFF `name` is a CRDS-style name, e.g. hst_acs.imap
    
    >>> newstyle_name("s7g1700gl_dead.fits")
    False
    >>> newstyle_name("hst.pmap")
    True
    >>> newstyle_name("hst_acs_darkfile_0001.fits")
    True
    """
    return name.startswith(("hst", "jwst", "tobs"))

def newer(name1, name2):
    """Determine if `name1` is a more recent file than `name2` accounting for 
    limited differences in naming conventions. Official CDBS and CRDS names are 
    comparable using a simple text comparison,  just not to each other.
    
    >>> newer("s7g1700gl_dead.fits", "hst_cos_deadtab_0001.fits")
    False
    >>> newer("hst_cos_deadtab_0001.fits", "s7g1700gl_dead.fits")
    True
    >>> newer("s7g1700gl_dead.fits", "bbbbb.fits")
    True
    >>> newer("bbbbb.fits", "s7g1700gl_dead.fits")
    False
    >>> newer("hst_cos_deadtab_0001.rmap", "hst_cos_deadtab_0002.rmap")
    False
    >>> newer("hst_cos_deadtab_0002.rmap", "hst_cos_deadtab_0001.rmap")
    True
    """
    if newstyle_name(name1):
        if newstyle_name(name2): # compare CRDS names
            result = name1 > name2
        else:  # CRDS > CDBS
            result = True
    else:
        if newstyle_name(name2):  # CDBS < CRDS
            result = False
        else:  # compare CDBS names
            result = name1 > name2
    log.verbose("Comparing filename time order:", repr(name1), ">", repr(name2), "-->", result)
    return result

# ============================================================================
        
def fits_difference(observatory, file1, file2):
    """Run fitsdiff on files named `file1` and `file2`.
    """
    assert file1.endswith(".fits"), \
        "File " + repr(file1) + " is not a FITS file."
    assert file2.endswith(".fits"), \
        "File " + repr(file2) + " is not a FITS file."
    loc_file1 = rmap.locate_file(file1, observatory)
    loc_file2 = rmap.locate_file(file2, observatory)
    fd = FITSDiff(loc_file1, loc_file2)
    if not fd.identical:
        fd.report(fileobj=sys.stdout)

def text_difference(observatory, file1, file2):
    """Run UNIX diff on two text files named `file1` and `file2`.
    """
    assert os.path.splitext(file1)[-1] == os.path.splitext(file2)[-1], \
        "Files " + repr(file1) + " and " + repr(file2) + " are of different types."
    _loc_file1 = rmap.locate_file(file1, observatory)
    _loc_file2 = rmap.locate_file(file2, observatory)
    pysh.sh("diff -b -c ${_loc_file1} ${_loc_file2}")

def difference(observatory, file1, file2, primitive_diffs=False, check_diffs=False, mapping_text_diffs=False):
    """Difference different kinds of CRDS files (mappings, FITS references, etc.)
    named `file1` and `file2` against one another and print out the results 
    on stdout.
    """
    if rmap.is_mapping(file1):
        mapping_difference(observatory, file1, file2, primitive_diffs=primitive_diffs, check_diffs=check_diffs,
                           mapping_text_diffs=mapping_text_diffs)
    elif file1.endswith(".fits"):
        fits_difference(observatory, file1, file2)
    else:
        text_difference(observatory, file1, file2)

# =============================================================================
 
class DiffScript(cmdline.Script):
    """Python command line script to difference mappings or references."""
    
    description = """Difference CRDS mapping or reference files."""
    
    epilog = """Reference files are nominally differenced using FITS-diff or diff.
    
Mapping files are differenced using CRDS machinery to recursively compare too mappings and 
their sub-mappings.
    
Differencing two mappings will find all the logical differences between the two contexts
and any nested mappings.
    
By specifying --mapping-text-diffs,  UNIX diff will be run on mapping files in addition to 
CRDS logical diffs.
    
By specifying --primitive-diffs,  FITS diff will be run on all references which are replaced
in the logical differences between two mappings.
    
For example:
    
    % python -m crds.diff hst_0001.pmap  hst_0005.pmap  --mapping-text-diffs --primitive-diffs
    
Will recursively produce logical, textual, and FITS diffs for all changes between the two contexts.
    
    NOTE: mapping logical differences (the default) to not compare CRDS mapping headers.
    """
    
    def add_args(self):
        """Add diff-specific command line parameters."""
        self.add_argument("old_file",  help="Prior file of difference.""")
        self.add_argument("new_file",  help="New file of difference.""")
        self.add_argument("-P", "--primitive-diffs", dest="primitive_diffs",
            help="Fitsdiff replaced reference files when diffing mappings.", 
            action="store_true")
        self.add_argument("-T", "--mapping-text-diffs",  dest="mapping_text_diffs", action="store_true",
            help="In addition to CRDS mapping logical differences,  run UNIX context diff for mappings.")
        self.add_argument("-K", "--check-diffs", dest="check_diffs", action="store_true",
            help="Issue warnings about new rules, deletions, or reversions.")
        self.add_argument("-N", "--print-new-files", dest="print_new_files", action="store_true",
            help="Rather than printing diffs for mappings,  print the names of new or replacement files.")

    def main(self):
        """Perform the differencing."""
        if self.args.print_new_files:
            return self.print_new_files()
        else:
            return difference(self.observatory, self.args.old_file, self.args.new_file, 
                   primitive_diffs=self.args.primitive_diffs, check_diffs=self.args.check_diffs,
                   mapping_text_diffs=self.args.mapping_text_diffs)
    
    def print_new_files(self):
        """Print the references or mappings which are new additions or replacements when comparing mappings."""
        if not rmap.is_mapping(self.args.old_file) or not rmap.is_mapping(self.args.new_file):
            log.error("--print-new-files really only works for mapping differences.")
            return -1
        diffs = mapping_diffs(self.args.old_file, self.args.new_file)
        categorized = sorted([ (diff_action(d), d) for d in diffs ])
        for action, diff in categorized:
            if action == "add":
                added = diff_added_new(diff)
                print self.instrument_filekind(added), added
            elif action == "replace":
                _old_val, replacement = map(os.path.basename, diff_replace_old_new(diff))
                print self.instrument_filekind(replacement), replacement
    
    def instrument_filekind(self, filename):
        """Return the instrument and filekind of `filename` as a space separated string."""
        instrument, filekind = utils.get_file_properties(self.observatory, filename)
        return instrument + " " + filekind 

        
        
if __name__ == "__main__":
    DiffScript()()
