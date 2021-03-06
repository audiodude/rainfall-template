from collections import defaultdict
from datetime import datetime
import markdown
import random
import sys
import os

from flask import Flask
from flask import Markup
from flask import render_template
from flask import request
from flask_frozen import Freezer
from pymongo import MongoClient

client = MongoClient(connect=False)
rainfall_db= client.rainfall

app = Flask(__name__)
freezer = Freezer(app)

song_colors = [
  '#FD7632',
  '#477C90',
  '#4B0082',
  '#CD4640',
  '#85D817',
  '#DDB8C7',
  '#2AC8C6',
]

def _annotate(song, i):
  if 'src' in song:
    return
  song['src'] = '/static/mp3/' + song['slug'] + '.mp3'
  song['dt'] = datetime.fromtimestamp(song['date_created'])
  _add_color(song, i)

def _add_color(song, i):
  song['color'] = song_colors[i % len(song_colors)]

@app.route('/')
def index():
  if (os.environ.get('CHECK_REFERER') and
      request.headers.get("Referer") != 'https://rainfall.dev/edit'):
    return ('Not Authorized', 403)

  site_id = os.environ.get('RAINFALL_SITE_ID')
  if site_id is None:
    return ('Not Found', 404)

  site = rainfall_db.sites.find_one({'site_id': site_id})
  if site is None:
    return ('Not Found', 404)

  songs = site.get('songs', [])

  for i, song in enumerate(songs):
    _annotate(song, i)

  sorted_songs = sorted(list(songs), key=lambda song: song['dt'], reverse=True)

  # Re-add the colors once the songs are sorted.
  for i, song in enumerate(sorted_songs):
    _add_color(song, i)

  header = Markup(markdown.markdown(site['header']))
  footer = Markup(markdown.markdown(site['footer']))

  return render_template(
    'index.html', songs=sorted_songs, header=header, footer=footer)

@app.route('/<slug>/')
def song(slug):
  related = defaultdict(list)

  if (os.environ.get('CHECK_REFERER') and
      'rainfall.dev' not in request.headers.get("Referer")):
    return ('Not Authorized', 403)

  site_id = os.environ.get('RAINFALL_SITE_ID')
  if site_id is None:
    return ('Not Found', 404)

  site = rainfall_db.sites.find_one({'site_id': site_id})
  if site is None:
    return ('Not Found', 404)

  songs = site.get('songs', [])
  if not songs:
    return flask.redirect('/')

  for song in songs:
    if song['slug'] == slug:
      break

  _annotate(song, random.randrange(0, len(song_colors)))

  faq = Markup(markdown.markdown(site.get('faq', '')))

  for tag in song['tags']:
    for i, s in enumerate(songs):
      if tag in s['tags']:
        _annotate(s, i)
        if s['slug'] != song['slug']:
          related[tag].append(s)
  song['related'] = related
  song['src'] = '/static/mp3/' + slug + '.mp3'
  song['description_html'] = Markup(markdown.markdown(song['description']))
  return render_template('song.html', song=song, title=song['name'])

if __name__ == '__main__':
  if len(sys.argv) > 1 and sys.argv[1] == 'build':
    freezer.freeze()
  else:
    app.run()
