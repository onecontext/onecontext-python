from onecontext import OneContext
from dotenv import load_dotenv
config = load_dotenv()

oc = OneContext()
ctx = oc.Context("demo")

ctx.list_files()[0].metadata_json

good_update_object = {
    "WhatisLove": "BabyDontHurtMe",
    "DontHurtMe" : "NoMore"
}

bad_update_object = {
    "file_id" : "stone-cold",
    "steve" : "austin"
}

ctx.update_file_meta(file_id="0fb55bcf-4c89-409a-969e-284b6b011527", update_object=good_update_object)
ctx.clear_file_meta(file_id="0fb55bcf-4c89-409a-969e-284b6b011527")


