import os

output_file = 'Clinical_Couture_Frontend_Code.txt'
folders = ['templates', 'static/css', 'static/js']

with open(output_file, 'w', encoding='utf-8') as outfile:
    outfile.write('--- UI/FRONTEND CODEBASE FOR CLINICAL COUTURE ---\n\n')
    for folder in folders:
        for root, _, files in os.walk(folder):
            for file in files:
                filepath = os.path.join(root, file)
                outfile.write(f'{"=" * 80}\n')
                outfile.write(f'FILE: {filepath}\n')
                outfile.write(f'{"=" * 80}\n\n')
                try:
                    with open(filepath, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                        outfile.write('\n\n')
                except Exception as e:
                    outfile.write(f'Error reading file: {e}\n\n')

print(f'Successfully created {output_file}')
