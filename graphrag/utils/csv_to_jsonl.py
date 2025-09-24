import csv
import json
import os

input_csv_path = '/Users/matthewtaruno/dev/hestia/data/brain.csv'  # path to your CSV file
output_jsonl_path = '/Users/matthewtaruno/dev/hestia/data/brain.jsonl'  # where the JSONL file will go

def convert_csv_to_jsonl(csv_path, jsonl_path):
    with open(csv_path, newline='', encoding='utf-8') as csvfile, open(jsonl_path, 'w', encoding='utf-8') as jsonlfile:
        reader = csv.DictReader(csvfile)

        # Print all column names to verify we're capturing everything
        print("CSV Columns:", reader.fieldnames)

        for row in reader:
            main_text = row['Paragraph or Advice Text (Main Content Here)'].strip()
            if not main_text:
                continue  # skip rows without content

            # Get the actionable advice from the Intervention Suggested column
            actionable_advice = row.get("Intervention Suggested (Actionable)", "").strip()

            # Combine the main text with the actionable advice if available
            full_content = main_text
            if actionable_advice:
                # Add the actionable advice as a separate paragraph
                full_content = f"{main_text}\n\nActionable Advice: {actionable_advice}"

            data = {
                "title": row["Title of Advice"].strip(),
                "full_text": {
                    "content": full_content
                },
                "source": {
                    "type": row.get("What type of source is this?", "").strip(),
                    "name": row.get("Source Name", "").strip(),
                    "url": row.get("Source URL ", "").strip()
                },
                "tags": {
                    "Main Topic Entities": [e.strip() for e in row.get("Main Topic Entities", "").split(",") if e.strip()],
                    "Sub-entities": [s.strip() for s in row.get("Sub-entities (If multiple other give as comma separated entries)", "").split(",") if s.strip()],
                    "Age Range": [a.strip() for a in row.get("Child Age Range (check all applicable)", "").split(",") if a.strip()],
                    "Guidance Style": [g.strip() for g in row.get("Guidance Style", "").split(",") if g.strip()]
                },
                "author": row.get("Author", "").strip(),
                "credentials": row.get("Credentials / Area of Expertise\ne.g. Ph.D. in Child Psychology, Licensed Clinical Psychologist", "").strip(),
                "temporal_context": row.get("Temporal Context (Only add if relevant)", "").strip(),
                "scenario_notes": row.get("What scenario would this be especially useful for? (e.g. tone, cultural fit, edge cases, or special considerations)", "").strip(),
                "actionable_advice": actionable_advice  # Also store it separately for direct access
            }

            json.dump(data, jsonlfile, ensure_ascii=False)
            jsonlfile.write('\n')

    print(f"✅ Converted CSV to JSONL at {jsonl_path}")

if __name__ == "__main__":
    convert_csv_to_jsonl(input_csv_path, output_jsonl_path)