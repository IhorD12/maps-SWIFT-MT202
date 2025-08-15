import re
import json
from datetime import datetime

def parse_mt202(raw_message: str) -> dict:
    """
    Parses a raw SWIFT MT202 message text and returns a structured dictionary.
    This version handles multiline fields correctly.
    """
    fields = {}
    current_tag = None

    for line in raw_message.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.startswith(':'):
            try:
                # Format is :TAG:VALUE
                _, tag, value = line.split(':', 2)
                current_tag = tag
                fields[current_tag] = value
            except ValueError:
                # Handle cases like :TAG: without a value on the same line
                parts = line.split(':')
                if len(parts) > 1:
                    current_tag = parts[1]
                    fields[current_tag] = "" # No value yet
        elif current_tag:
            # This is a continuation of the previous field
            fields[current_tag] += '\n' + line

    parsed = {}
    if '20' in fields:
        parsed['transaction_reference'] = fields['20']
    if '21' in fields:
        parsed['related_reference'] = fields['21']

    if '32A' in fields:
        data = fields['32A']
        date_str = data[:6]
        parsed['value_date'] = datetime.strptime(f"20{date_str}", "%Y%m%d").strftime("%Y-%m-%d")
        parsed['currency'] = data[6:9]
        parsed['amount'] = float(data[9:].replace(',', '.'))

    if '50A' in fields:
        parsed['ordering_institution'] = fields['50A']
    elif '50K' in fields:
        # Field 50K can have multiple lines
        parsed['ordering_institution'] = fields['50K'].replace('\n', ' ').strip()

    if '52A' in fields:
        parsed['ordering_agent'] = fields['52A']
    if '57A' in fields:
        parsed['account_with_institution'] = fields['57A']
    if '59' in fields:
        # Field 59 can also be multiline
        parsed['beneficiary'] = fields['59'].replace('\n', ' ').strip()
    if '71A' in fields:
        parsed['charges'] = fields['71A']
    if '72' in fields:
        parsed['sender_to_receiver_info'] = fields['72'].replace('\n', ' ').strip()

    return parsed

if __name__ == '__main__':
    # Example usage with a sample MT202 message
    sample_mt202 = """
:20:TXREF12345
:21:RELREF67890
:32A:240815USD12345.67
:50K:/12345678
ORDERING BANK NAME
CITY
:52A:ORDERINGAGENTBIC
:57A:BENEFICIARYBANKBIC
:59:/987654321
BENEFICIARY NAME
ADDRESS LINE 1
:71A:OUR
:72:/SND2REC/INFO
SOME MORE INFO
"""
    parsed_message = parse_mt202(sample_mt202)
    print(json.dumps(parsed_message, indent=4))

    # Test another one
    sample_2 = ":20:ANOTHERREF\n:32A:250101EUR999,00\n:57A:SOMEOTHERBIC"
    parsed_2 = parse_mt202(sample_2)
    print(json.dumps(parsed_2, indent=4))
