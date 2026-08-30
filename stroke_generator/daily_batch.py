import os
import sys
import json
import subprocess
from pathlib import Path
from collections import defaultdict
import gspread
from google.oauth2 import service_account
from gspread_formatting import CellFormat, Color, format_cell_range

# --- CONFIGURATION ---
SPREADSHEET_ID = '1VwIvQuTCEy6RcL8tDWJ3VRAuCuCB2rePzngIg0Mj16k'
WORKSHEET_NAME = 'hanzi'
APP_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = APP_ROOT / 'output'

# --- AUTHENTICATION ---
# The GOOGLE_CREDENTIALS environment variable will be provided by GitHub Actions Secrets
credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
if not credentials_json:
    raise ValueError("GOOGLE_CREDENTIALS environment variable is not set!")

info = json.loads(credentials_json)
creds = service_account.Credentials.from_service_account_info(
    info, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
)

gc = gspread.authorize(creds)

print("✅ Authenticated successfully with Google Service Account.")

# --- CONNECT TO SHEET ---
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
rows = worksheet.get_all_values()
if not rows:
    raise ValueError('Sheet is empty')

header = rows[0]
data_rows = rows[1:]

while len(header) < 7:
    header.append('')
if header[6] != 'Error Log':
    worksheet.update(values=[['Error Log']], range_name='G1')
    header[6] = 'Error Log'

# --- HELPER FUNCTIONS ---
def normalize_hanzi(value):
    return (value or '').strip()

def should_generate(status, filename, drive_link):
    value = (status or '').strip().upper()
    if value == 'DONE':
        return False, 'Status=DONE'
    if value == 'RUN':
        return True, 'Status=RUN'
    if value == 'ERROR':
        return True, 'Status=ERROR (rerun)'
    if filename.strip() and drive_link.strip():
        return False, 'Already has filename + link'
    return True, 'Missing output'

# --- GITHUB RAW URL ---
def get_github_raw_url(filename):
    # GitHub URL format for raw files in the repo
    import urllib.parse
    safe_filename = urllib.parse.quote(filename)
    return f"https://raw.githubusercontent.com/alerondt-hanario/hanzi-generator-actions/main/output/{safe_filename}"

# --- CHECK DUPLICATES ---
hanzi_map = defaultdict(list)
for idx, row in enumerate(data_rows, start=2):
    hanzi = normalize_hanzi(row[1] if len(row) > 1 else '')
    if hanzi:
        hanzi_map[hanzi].append(idx)

duplicate_rows = {hanzi: indices for hanzi, indices in hanzi_map.items() if len(indices) > 1}

RED_FILL = CellFormat(backgroundColor=Color(1, 0.85, 0.85))
CLEAR_FILL = CellFormat(backgroundColor=Color(1, 1, 1))
ORANGE_FILL = CellFormat(backgroundColor=Color(1, 0.92, 0.8))

for row_index, row in enumerate(data_rows, start=2):
    hanzi = normalize_hanzi(row[1] if len(row) > 1 else '')
    warning = ''
    if hanzi and hanzi in duplicate_rows:
        duplicate_line_list = ', '.join(map(str, duplicate_rows[hanzi]))
        warning = f'TRÙNG: {hanzi} ở dòng {duplicate_line_list}'
        format_cell_range(worksheet, f'B{row_index}:G{row_index}', RED_FILL)
    else:
        format_cell_range(worksheet, f'B{row_index}:G{row_index}', CLEAR_FILL)
    
    worksheet.update(values=[[warning]], range_name=f'C{row_index}')

# --- PROCESS ---
generated_count = 0
skipped_count = 0
error_count = 0
error_rows = []
done_rows = []
skipped_rows = []

# Ensure Puppeteer skips chromium download since GitHub Actions already has Chrome if we use setup-chrome, 
# actually GitHub Actions Ubuntu runner comes with Chrome installed. We can just let Puppeteer download it locally to avoid path issues.
env = os.environ.copy()

for row_index, row in enumerate(data_rows, start=2):
    hanzi = normalize_hanzi(row[1] if len(row) > 1 else '')
    status = row[3] if len(row) > 3 else ''
    filename_cell = row[4] if len(row) > 4 else ''
    link_cell = row[5] if len(row) > 5 else ''

    if not hanzi:
        skipped_count += 1
        skipped_rows.append((row_index, 'Missing Hanzi in column B'))
        continue

    should_run, reason = should_generate(status, filename_cell, link_cell)
    if not should_run:
        skipped_count += 1
        skipped_rows.append((row_index, reason))
        continue

    print(f"Processing row {row_index}: {hanzi} ...")
    try:
        subprocess.run(
            ['npm', 'run', 'generate', '--', hanzi],
            cwd=str(APP_ROOT),
            env=env,
            check=True
        )

        filename = f'{hanzi}.gif'
        generated_gif = OUTPUT_DIR / filename
        if not generated_gif.exists():
            raise FileNotFoundError(f'Cannot find generated GIF: {generated_gif}')

        drive_link = get_github_raw_url(filename)

        worksheet.update(values=[[filename, drive_link, '']], range_name=f'E{row_index}:G{row_index}')
        worksheet.update(values=[['DONE']], range_name=f'D{row_index}')
        if hanzi not in duplicate_rows:
            format_cell_range(worksheet, f'B{row_index}:G{row_index}', CLEAR_FILL)
        generated_count += 1
        done_rows.append((row_index, hanzi, filename))
        print(f"  -> Success! Link: {drive_link}")
    except Exception as error:
        error_message = str(error).replace('\n', ' ')[:500]
        worksheet.update(values=[['ERROR', '', '', error_message]], range_name=f'D{row_index}:G{row_index}')
        format_cell_range(worksheet, f'B{row_index}:G{row_index}', ORANGE_FILL)
        error_count += 1
        error_rows.append((row_index, hanzi, error_message))
        print(f"  -> Failed: {error_message}")

print('\n===== SUMMARY =====')
print(f'Thành công: {generated_count}')
print(f'Bỏ qua   : {skipped_count}')
print(f'Lỗi      : {error_count}')
