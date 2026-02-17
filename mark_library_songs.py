"""
Temp script: Mark the 25 previously-hardcoded library songs as is_library=True.
Run with: python manage.py shell < mark_library_songs.py
Delete this file after running.
"""
from api.models import Song

LIBRARY_IDS = [174, 149, 150, 151, 152, 153, 154, 155, 156, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173]

updated = Song.objects.filter(id__in=LIBRARY_IDS).update(is_library=True)
print(f"Marked {updated} songs as is_library=True")

# Verify
missing = set(LIBRARY_IDS) - set(Song.objects.filter(id__in=LIBRARY_IDS).values_list('id', flat=True))
if missing:
    print(f"Warning: song IDs not found in DB: {missing}")
else:
    print("All song IDs found.")
