# @retry(tries=2, delay=5)
# def process_gpt(system, prompt):
#     completion = openai.ChatCompletion.create(
#         #engine="gpt-4-32k",
#         #model="gpt-4-32k",
#         engine=model_name,
#         model=model_name,
#         max_tokens=16384,
#         # Try to be as deterministic as possible
#         temperature=0,
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user", "content": prompt},
#         ]
#     )
#     nlp_results = completion.choices[0].message.content
#     return nlp_results


# def clean_text(text):
#   clean = "\n".join([row for row in text.split("\n")])
#   clean = re.sub(r'\(fig[^)]*\)', '', clean, flags=re.IGNORECASE)
#   return clean