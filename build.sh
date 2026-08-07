#!/usr/bin/env bash
# Render build command. Xato bo'lsa darhol to'xtaydi.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
