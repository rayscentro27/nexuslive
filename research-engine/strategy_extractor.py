import os

INPUT = "./summaries"
OUTPUT = "./strategies"

os.makedirs(OUTPUT, exist_ok=True)

for file in os.listdir(INPUT):
    if file.endswith('.summary'):
        with open(os.path.join(INPUT, file), 'r', encoding='utf-8') as f:
            text = f.read()

        # Filter for content that contains trading strategies
        if any(keyword in text.lower() for keyword in ['strategy', 'indicator', 'risk', 'trade', 'setup']):
            with open(os.path.join(OUTPUT, file), "w", encoding='utf-8') as out:
                out.write(text)
            print(f"Extracted strategy from: {file}")