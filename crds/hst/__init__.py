"""
>>> TYPES.get_row_keys_by_instrument("wfpc2")
['detchip', 'detector', 'direction', 'filter', 'filter1', 'filter2', 'obsdate', 'theta']

>>> TYPES.suffix_to_filekind("acs","drk")
'darkfile'

>>> TYPES.filetype_to_filekind("stis", "dark image")
'darkfile'

>>> TYPES.get_filekinds("wfpc2")
['atodfile', 'biasfile', 'darkfile', 'dgeofile', 'flatfile', 'idctab', 'maskfile', 'offtab', 'shadfile', 'wf4tfile']

>>> TYPES.mapping_validator_key("hst_acs_darkfile.rmap")
('acs_drk_ld.tpn',)

>>> from crds import config

>> TYPES.reference_name_to_ld_tpn_key(config.locate_file("pcc2026io_lfl.fits", "hst"))
('stis_lfl_ld.tpn',)

>> TYPES.reference_name_to_ld_tpn_key(config.locate_file("iaf1723io_lfl.fits", "hst"))
('stis_lfl_ld.tpn',)

>> TYPES.reference_name_to_validator_key(config.locate_file("pcc2026io_lfl.fits", "hst"))
('stis_slfl.tpn',)

>> TYPES.reference_name_to_validator_key(config.locate_file("iaf1723io_lfl.fits", "hst"))
('stis_ilfl.tpn',)

"""

import os.path

from crds import reftypes

TYPES = reftypes.from_package_file(__file__)

INSTRUMENTS = TYPES.instruments
EXTENSIONS = TYPES.extensions
TEXT_DESCR = TYPES.text_descr
FILEKINDS = TYPES.filekinds

HERE  = os.path.dirname(__file__) or "."

INSTRUMENT_FIXERS = {
    "wfii": "wfpc2",
}

TYPE_FIXERS = {
    ("wfpc2","dark") : "drk", 
}


def test():
    """Run hst package doctests."""
    from crds import hst
    import doctest
    return doctest.testmod(hst)
