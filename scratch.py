from onecontext import OneContext
from dotenv import load_dotenv
from pydantic import BaseModel, Field

config = load_dotenv()
oc = OneContext()
context = oc.Context("what")

class RockBandInfo(BaseModel):
    title: str = Field(description="a title of a 1970s rockband")
    lyrics: str = Field(description="lyrics to their absolute banger of a song")

len(context.list_files(metadata_filters={"rockband": {"$eq":"yes"}}))
context.list_files()

len(context.list_files(metadata_filters={"rockband": {"$eq":"yes"}}, file_ids=["2e61ab82-d631-4a24-ba6c-4d030ca9280a"], get_download_urls=True))
context.list_files(metadata_filters={"rockband": {"$eq":"no"}}, file_names=["OneContext Privacy Policy.docx"])

context.list_files(metadata_filters={"rockband": {"$eq":"no"}}, file_names=["OneContext Privacy Policy.docx"], get_download_urls=False)

context.upload_from_directory(directory="./tests/files",metadata={"rockband": "no"})




output_dict, chunks = context.extract_from_search(
    query="tell me about rockbands",
    schema=RockBandInfo, # you can pass a pydantic (v2) model or a json schema dict
    extraction_prompt="Output only JSON matching the provided schema about the rockbands",
)

rock_band = RockBandInfo.model_validate(output_dict)

good_update_object = {
    "WhatisLove": "BabyDontHurtMe",
    "DontHurtMe" : "NoMore",
    "ERMAHGERG": "yes"
}

bad_update_object = {
    "file_id" : "stone-cold",
    "steve" : "austin"
}

ctx.update_file_meta(file_id="0fb55bcf-4c89-409a-969e-284b6b011527", update_object=good_update_object)
ctx.clear_file_meta(file_id="0fb55bcf-4c89-409a-969e-284b6b011527")


