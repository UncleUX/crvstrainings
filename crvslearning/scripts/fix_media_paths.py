import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crvslearning.settings')
import django

django.setup()

from courses.models import Course, Lesson

def fix_paths():
    cc = 0
    for c in Course.objects.exclude(thumbnail=''):
        if c.thumbnail and c.thumbnail.name.startswith('media/'):
            c.thumbnail.name = c.thumbnail.name[6:]
            c.save(update_fields=['thumbnail'])
            cc += 1

    lc = 0
    for l in Lesson.objects.all():
        upd = []
        if l.video_file and l.video_file.name.startswith('media/'):
            l.video_file.name = l.video_file.name[6:]
            upd.append('video_file')
        if l.content_file and l.content_file.name.startswith('media/'):
            l.content_file.name = l.content_file.name[6:]
            upd.append('content_file')
        if l.thumbnail and l.thumbnail.name.startswith('media/'):
            l.thumbnail.name = l.thumbnail.name[6:]
            upd.append('thumbnail')
        if upd:
            l.save(update_fields=upd)
            lc += 1

    print(f"Courses fixed: {cc}, Lessons fixed: {lc}")

if __name__ == '__main__':
    fix_paths()
