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
  if hasattr(song, 'slug'):
    return
  slug = os.path.basename(song.path)
  song.src = '/static/mp3/' + slug + '.mp3'
  song.slug = slug
  song.dt = datetime.strptime(song.meta['date'], '%Y/%m/%d')
  _add_color(song, i)

def _add_color(song, i):
  song.color = song_colors[i % len(song_colors)]

@app.route('/')
def index():
  if (os.environ.get('CHECK_REFERER') and
      request.headers.get("Referer") != 'https://rainfall.dev/edit'):
    return ('Not Authorized', 403)

  site_id = os.environ.get('RAINFALL_SITE_ID')
  if site_id is None:
    return ('Not Found', 404)

  # for i, song in enumerate(songs):
  #   _annotate(song, i)

  # sorted_songs = sorted(list(songs), key=lambda song: song.dt, reverse=True)

  # # Re-add the colors once the songs are sorted.
  # for i, song in enumerate(sorted_songs):
  #   _add_color(song, i)

  # TODO: Get the above working with mongo.
  sorted_songs = []

  site = rainfall_db.sites.find_one({'site_id': site_id})
  if site is None:
    return ('Not Found', 404)

  header = Markup(markdown.markdown(site['header']))
  footer = Markup(markdown.markdown(site['footer']))

  return render_template(
    'index.html', songs=sorted_songs, header=header, footer=footer)

@app.route('/<path:path>/')
def song(path):
  related = defaultdict(list)

  song = songs.get_or_404(path)
  _annotate(song, random.randrange(0, len(song_colors)))

  for tag in song.meta['tags']:
    for i, s in enumerate(songs):
      if tag in s.meta['tags']:
        _annotate(s, i)
        if s.slug != song.slug:
          related[tag].append(s)
  song.related = related
  song.src = '/static/mp3/' + os.path.basename(path) + '.mp3'
  return render_template('song.html', song=song, title=song.meta['title'])

if __name__ == '__main__':
  if len(sys.argv) > 1 and sys.argv[1] == 'build':
    freezer.freeze()
  else:
    app.run()
