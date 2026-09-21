import json
import re

log_path = r'C:\Users\harsh\.gemini\antigravity-ide\brain\a3ba201d-f958-4000-949d-c004e32c57b5\.system_generated\logs\transcript_full.jsonl'

original_file_content = None

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        if '1: import smtplib' in line and '532: ' in line:
            # We found the line. Let's parse it as json.
            data = json.loads(line)
            # The content could be in data['content']
            content = data.get('content', '')
            if 'The above content shows the entire, complete file contents of the requested file.' in content:
                # Good, let's extract the lines
                lines = content.split('\n')
                extracted = []
                capture = False
                for l in lines:
                    if l.startswith('1: import smtplib'):
                        capture = True
                    if l.startswith('The above content shows'):
                        break
                    if capture:
                        idx = l.find(': ')
                        if idx != -1 and l[:idx].isdigit():
                            extracted.append(l[idx+2:])
                original_file_content = '\n'.join(extracted)
                break

if original_file_content:
    original_file_content = original_file_content.replace(
        '        db = client.get_default_database()',
        '''        if not hasattr(client.__class__, 'append_metadata'):
            client.__class__.append_metadata = lambda *args, **kwargs: None
        db = client["gc25"]'''
    )
    with open('backend/tasks.py', 'w', encoding='utf-8') as fw:
        fw.write(original_file_content)
    print('Restored and fixed backend/tasks.py successfully!')
else:
    print('Failed to find original content in transcript.')
