"""task_job_scam: keyword-lexicon check. Edit the patterns in core/data.py -> KW['task_job']."""
from .common import lexicon_check


lexicon_check('task_job_scam', 'task_job', 'H', 40,
              'Part-time/task/like-and-earn job offer, usually moved to Telegram', 'task-job lure')
