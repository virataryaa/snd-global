"""The ten origins: which coffee type, where the numbers come from, and the TDM reporter code.

source = "tdm"    -> months not in the history / manual files are filled from TDM exports (tonnes / 0.06 = 60 kg bags)
source = "manual" -> only the history file and what is typed on the Entry page
share  = fraction of the TDM tonnage counted (India / Indonesia export both types; the history is the Robusta part).
Database/settings.json {"tdm_share": {"India": 0.65}} overrides the defaults below, so they can be tuned without code.
"""

BAGS_PER_TONNE = 1000 / 60            # 60 kg bags

ORIGINS = [
    dict(name="Brazil Arabica", type="Arabica", reporter="BR", source="manual"),
    dict(name="Colombia",       type="Arabica", reporter="CO", source="manual"),
    dict(name="Honduras",       type="Arabica", reporter="HN", source="tdm", share=1.0),
    dict(name="Ethiopia",       type="Arabica", reporter="ET", source="tdm", share=1.0),
    dict(name="Peru",           type="Arabica", reporter="PE", source="tdm", share=1.0),
    dict(name="Vietnam",        type="Robusta", reporter="VN", source="manual"),
    dict(name="Brazil Robusta", type="Robusta", reporter="BR", source="manual"),
    dict(name="Indonesia",      type="Robusta", reporter="ID", source="tdm", share=1.0),
    dict(name="Uganda",         type="Robusta", reporter="UG", source="manual"),
    dict(name="India",          type="Robusta", reporter="IN", source="tdm", share=1.0),
]
NAMES = [o["name"] for o in ORIGINS]
BY_NAME = {o["name"]: o for o in ORIGINS}
TYPES = ["Arabica", "Robusta"]
