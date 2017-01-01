#!/usr/bin/python

"""
The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

# For a complete discussion, see http://forum.kodi.tv/showthread.php?tid=254502

import datetime
import pytz
import random
import string
import sys
import time
import os
from multiprocessing import Process
from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement

sys.path += [os.path.dirname(__file__)]

import kodi

kodi.PopulateEnv()

app = Flask(__name__)

SKILL_ID = os.getenv('SKILL_APPID')
if SKILL_ID and SKILL_ID != 'None':
  app.config['ASK_APPLICATION_ID'] = SKILL_ID

# According to this: https://alexatutorial.com/flask-ask/configuration.html
# Timestamp based verification shouldn't be used in production. Use at own risk
# app.config['ASK_VERIFY_TIMESTAMP_DEBUG'] = True

# Needs to be instanced after app is configured
ask = Ask(app, "/")

# Start of intent methods

# Handle the NewShowInquiry intent.
@ask.intent('NewShowInquiry')
def alexa_new_show_inquiry(Show):
  heard_show = str(Show).lower().translate(None, string.punctuation)

  card_title = render_template('looking_for_show', heard_show=heard_show)
  print card_title

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episodes_result = kodi.GetUnwatchedEpisodesFromShow(located['tvshowid'])

      if not 'episodes' in episodes_result['result']:
        num_of_unwatched = 0

      else:
        num_of_unwatched = len(episodes_result['result']['episodes'])

      if num_of_unwatched > 0:
        if num_of_unwatched == 1:
          response_text = render_template('one_unseen_show', show_name=heard_show)
        else:
          response_text = render_template('multiple_unseen_show', show_name=heard_show, num=num_of_unwatched)

      else:
        response_text = render_template('no_unseen_show', show_name=heard_show)
    else:
      response_text = render_template('could_not_find', heard_name=heard_show)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the CurrentPlayItemInquiry intent.
@ask.intent('CurrentPlayItemInquiry')
def alexa_current_playitem_inquiry():
  card_title = render_template('current_playing_item')
  print card_title

  answer = 'The current'
  answer_append = 'ly playing item is unknown'

  try:
    curitem = kodi.GetActivePlayItem()
  except:
    answer = 'There is nothing current'
    answer_append = 'ly playing'
  else:
    if curitem is not None:
      if curitem['type'] == 'episode':
        # is a tv show
        answer += ' TV show is'
        answer_append = ' unknown'
        if curitem['showtitle']:
          answer += ' %s,' % (curitem['showtitle'])
          answer_append = ''
        if curitem['season']:
          answer += ' season %s,' % (curitem['season'])
          answer_append = ''
        if curitem['episode']:
          answer += ' episode %s,' % (curitem['episode'])
          answer_append = ''
        if curitem['title']:
          answer += ' %s' % (curitem['title'])
          answer_append = ''
      elif curitem['type'] == 'song' or curitem['type'] == 'musicvideo':
        # is a song (music video or audio)
        answer += ' song is'
        answer_append = ' unknown'
        if curitem['title']:
          answer += ' %s,' % (curitem['title'])
          answer_append = ''
        if curitem['artist']:
          answer += ' by %s,' % (curitem['artist'][0])
          answer_append = ''
        if curitem['album']:
          answer += ' on the album %s' % (curitem['album'])
          answer_append = ''
      elif curitem['type'] == 'movie':
        # is a video
        answer += ' movie is'
        answer_append = ' unknown'
        if curitem['title']:
          answer += ' %s' % (curitem['title'])
          answer_append = ''

    response_text = '%s%s.' % (answer, answer_append)
    return statement(response_text).simple_card(card_title, response_text)


# Handle the CurrentPlayItemTimeRemaining intent.
@ask.intent('CurrentPlayItemTimeRemaining')
def alexa_current_playitem_time_remaining():
  card_title = render_template('time_left_playing')
  print card_title

  response_text = 'Playback is stopped.'

  status = kodi.GetPlayerStatus()
  if status['state'] is not 'stop':
    minsleft = status['total_mins'] - status['time_mins']
    if minsleft == 0:
      response_text = 'It is nearly over.'
    elif minsleft == 1:
      response_text = 'There is one minute remaining.'
    elif minsleft > 1:
      response_text = 'There are %d minutes remaining' % (minsleft)
      tz = env('SKILL_TZ')
      if minsleft > 9 and tz and tz != 'None':
        utctime = datetime.datetime.now(pytz.utc)
        loctime = utctime.astimezone(pytz.timezone(tz))
        endtime = loctime + datetime.timedelta(minutes=minsleft)
        response_text += ', and it will end at %s.' % (endtime.strftime('%I:%M'))
      else:
        response_text += '.'

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayPause intent.
@ask.intent('PlayPause')
def alexa_play_pause():
  card_title = render_template('play_pause')
  print card_title

  kodi.PlayPause()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the AMAZON.StopIntent intent.
@ask.intent('AMAZON.StopIntent')
def alexa_stop():
  if not 'navigating' in session.attributes:
    card_title = render_template('stopping')
    print card_title

    kodi.Stop()
    response_text = "Playback stopped"

    return statement(response_text).simple_card(card_title, response_text)
  else:
    return statement("")


# Handle the PlayerSeekSmallForward intent.
@ask.intent('PlayerSeekSmallForward')
def alexa_player_seek_smallforward():
  card_title = render_template('step_forward')
  print card_title

  kodi.PlayerSeekSmallForward()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerSeekSmallBackward intent.
@ask.intent('PlayerSeekSmallBackward')
def alexa_player_seek_smallbackward():
  card_title = render_template('step_backward')
  print card_title

  kodi.PlayerSeekSmallBackward()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerSeekBigForward intent.
@ask.intent('PlayerSeekBigForward')
def alexa_player_seek_bigforward():
  card_title = render_template('big_step_forward')
  print card_title

  kodi.PlayerSeekBigForward()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerSeekBigBackward intent.
@ask.intent('PlayerSeekBigBackward')
def alexa_player_seek_bigforward():
  card_title = render_template('big_step_backward')
  print card_title

  kodi.PlayerSeekBigBackward()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ListenToArtist intent (Shuffles all music by an artist).
@ask.intent('ListenToArtist')
def alexa_listen_artist(Artist):
  heard_artist = str(Artist).lower().translate(None, string.punctuation)

  card_title = render_template('listen_artist', heard_artist=heard_artist)
  print card_title

  artists = kodi.GetMusicArtists()
  if 'result' in artists and 'artists' in artists['result']:
    artists_list = artists['result']['artists']
    located = kodi.matchHeard(heard_artist, artists_list, 'artist')

    if located:
      songs_result = kodi.GetArtistSongs(located['artistid'])
      songs = songs_result['result']['songs']

      songs_array = []

      for song in songs:
        songs_array.append(song['songid'])

      kodi.Stop()
      kodi.ClearAudioPlaylist()
      kodi.AddSongsToPlaylist(songs_array, True)
      kodi.StartAudioPlaylist()
      response_text = render_template('playing', heard_name=heard_artist)
    else:
      response_text = render_template('could_not_find', heard_name=heard_artist)
  else:
    response_text = render_template('could_not_find', heard_name=heard_artist)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ListenToAlbum intent (Play whole album, or whole album by a specific artist).
@ask.intent('ListenToAlbum')
def alexa_listen_album(Album, Artist):
  heard_album = str(Album).lower().translate(None, string.punctuation)
  card_title = render_template('playing_album_card')
  print card_title

  if Artist:
    heard_artist = str(Artist).lower().translate(None, string.punctuation)
    artists = kodi.GetMusicArtists()
    if 'result' in artists and 'artists' in artists['result']:
      artists_list = artists['result']['artists']
      located = kodi.matchHeard(heard_artist, artists_list, 'artist')

      if located:
        albums = kodi.GetArtistAlbums(located['artistid'])
        if 'result' in albums and 'albums' in albums['result']:
          albums_list = albums['result']['albums']
          album_located = kodi.matchHeard(heard_album, albums_list, 'label')

          if album_located:
            album_result = album_located['albumid']
            kodi.Stop()
            kodi.ClearAudioPlaylist()
            kodi.AddAlbumToPlaylist(album_result)
            kodi.StartAudioPlaylist()
            response_text = render_template('playing_album_artist', album_name=heard_album, artist=heard_artist)
          else:
            response_text = render_template('could_not_find_album_artist', album_name=heard_album, artist=heard_artist)
        else:
          response_text = render_template('could_not_find_album_artist', album_name=heard_album, artist=heard_artist)
      else:
        response_text = render_template('could_not_find_album_artist', album_name=heard_album, artist=heard_artist)
    else:
      response_text = render_template('could_not_find_album_artist', album_name=heard_album, artist=heard_artist)
  else:
    albums = kodi.GetAlbums()
    if 'result' in albums and 'albums' in albums['result']:
      albums_list = albums['result']['albums']
      album_located = kodi.matchHeard(heard_album, albums_list, 'label')

      if album_located:
        album_result = album_located['albumid']
        kodi.Stop()
        kodi.ClearAudioPlaylist()
        kodi.AddAlbumToPlaylist(album_result)
        kodi.StartAudioPlaylist()
        response_text = render_template('playing_album', album_name=heard_album)
      else:
        response_text = render_template('could_not_find_album', album_name=heard_album)
    else:
      response_text = render_template('could_not_find_album', album_name=heard_album)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ListenToSong intent (Play a song, or song by a specific artist).
@ask.intent('ListenToSong')
def alexa_listen_song(Song, Artist):
  heard_song = str(Song).lower().translate(None, string.punctuation)
  card_title = render_template('playing_song')
  print card_title

  if Artist:
    heard_artist = str(Artist).lower().translate(None, string.punctuation)
    artists = kodi.GetMusicArtists()
    if 'result' in artists and 'artists' in artists['result']:
      artists_list = artists['result']['artists']
      located = kodi.matchHeard(heard_artist, artists_list, 'artist')

      if located:
        songs = kodi.GetArtistSongs(located['artistid'])
        if 'result' in songs and 'songs' in songs['result']:
          songs_list = songs['result']['songs']
          song_located = kodi.matchHeard(heard_song, songs_list, 'label')

          if song_located:
            song_result = song_located['songid']
            kodi.Stop()
            kodi.ClearAudioPlaylist()
            kodi.AddSongToPlaylist(song_result)
            kodi.StartAudioPlaylist()
            response_text = render_template('playing_song_artist', song_name=heard_song, artist=heard_artist)
          else:
            response_text = render_template('could_not_find_song_artist', song_name=heard_song, artist=heard_artist)
        else:
          response_text = render_template('could_not_find_song_artist', song_name=heard_song, artist=heard_artist)
      else:
        response_text = render_template('could_not_find_song_artist', song_name=heard_song, artist=heard_artist)
    else:
      response_text = render_template('could_not_find_song_artist', song_name=heard_song, artist=heard_artist)
  else:
    songs = kodi.GetSongs()
    if 'result' in songs and 'songs' in songs['result']:
      songs_list = songs['result']['songs']
      song_located = kodi.matchHeard(heard_song, songs_list, 'label')

      if song_located:
        song_result = song_located['songid']
        kodi.Stop()
        kodi.ClearAudioPlaylist()
        kodi.AddSongToPlaylist(song_result)
        kodi.StartAudioPlaylist()
        response_text = render_template('playing_song', song_name=heard_song)
      else:
        response_text = render_template('could_not_find_song', song_name=heard_song)
    else:
      response_text = render_template('could_not_find_song', song_name=heard_song)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ListenToAlbumOrSong intent (Play whole album or song by a specific artist).
@ask.intent('ListenToAlbumOrSong')
def alexa_listen_album_or_song(Song, Album, Artist):
  if Song:
    heard_search = str(Song).lower().translate(None, string.punctuation)
  elif Album:
    heard_search = str(Album).lower().translate(None, string.punctuation)
  if Artist:
    heard_artist = str(Artist).lower().translate(None, string.punctuation)

  card_title = render_template('playing_album_or_song')
  print card_title

  artists = kodi.GetMusicArtists()
  if 'result' in artists and 'artists' in artists['result']:
    artists_list = artists['result']['artists']
    located = kodi.matchHeard(heard_artist, artists_list, 'artist')

    if located:
      albums = kodi.GetArtistAlbums(located['artistid'])
      if 'result' in albums and 'albums' in albums['result']:
        albums_list = albums['result']['albums']
        album_located = kodi.matchHeard(heard_search, albums_list, 'label')

        if album_located:
          album_result = album_located['albumid']
          kodi.Stop()
          kodi.ClearAudioPlaylist()
          kodi.AddAlbumToPlaylist(album_result)
          kodi.StartAudioPlaylist()
          response_text = render_template('playing_album_artist', album_name=heard_search, artist=heard_artist)
        else:
          songs = kodi.GetArtistSongs(located['artistid'])
          if 'result' in songs and 'songs' in songs['result']:
            songs_list = songs['result']['songs']
            song_located = kodi.matchHeard(heard_search, songs_list, 'label')

            if song_located:
              song_result = song_located['songid']
              kodi.Stop()
              kodi.ClearAudioPlaylist()
              kodi.AddSongToPlaylist(song_result)
              kodi.StartAudioPlaylist()
              response_text = render_template('playing_song_artist', song_name=heard_search, artist=heard_artist)
            else:
              response_text = render_template('could_not_find_song_artist', heard_name=heard_search, artist=heard_artist)
          else:
            response_text = render_template('could_not_find_song_artist', heard_name=heard_search, artist=heard_artist)
      else:
        response_text = render_template('could_not_find_song_artist', heard_name=heard_search, artist=heard_artist)
    else:
      response_text = render_template('could_not_find_song_artist', heard_name=heard_search, artist=heard_artist)
  else:
    response_text = render_template('could_not_find', heard_name=heard_artist)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ListenToAudioPlaylistRecent intent (Shuffle all recently added songs).
@ask.intent('ListenToAudioPlaylistRecent')
def alexa_listen_recently_added_songs():
  card_title = render_template('playing_recent_songs')
  response_text = render_template('no_recent_songs')
  print card_title

  songs_result = kodi.GetRecentlyAddedSongs()
  if songs_result:
    songs = songs_result['result']['songs']

    songs_array = []

    for song in songs:
      songs_array.append(song['songid'])

    kodi.Stop()
    kodi.ClearAudioPlaylist()
    kodi.AddSongsToPlaylist(songs_array, True)
    kodi.StartAudioPlaylist()
    response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ListenToAudioPlaylist intent.
@ask.intent('ListenToAudioPlaylist')
def alexa_listen_audio_playlist(AudioPlaylist, shuffle=False):
  heard_search = str(AudioPlaylist).lower().translate(None, string.punctuation)

  if shuffle:
    op = render_template('shuffling_empty')
  else:
    op = render_template('playing_empty')

  card_title = render_template('action_audio_playlist', action=op)
  print card_title

  playlist = kodi.FindAudioPlaylist(heard_search)
  if playlist:
    if shuffle:
      songs = kodi.GetPlaylistItems(playlist)['result']['files']

      songs_array = []

      for song in songs:
        songs_array.append(song['id'])

      kodi.Stop()
      kodi.ClearAudioPlaylist()
      kodi.AddSongsToPlaylist(songs_array, True)
      kodi.StartAudioPlaylist()
    else:
      kodi.Stop()
      kodi.StartAudioPlaylist(playlist)
    response_text = render_template('playing_playlist', action=op, playlist_name=heard_search)
  else:
    response_text = render_template('could_not_find_playlist', heard_name=heard_search)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ShuffleAudioPlaylist intent.
@ask.intent('ShuffleAudioPlaylist')
def alexa_shuffle_audio_playlist(AudioPlaylist):
  return alexa_listen_audio_playlist(AudioPlaylist, True)


# Handle the PartyMode intent.
@ask.intent('PartyMode')
def alexa_party_play():
  card_title = render_template('party_mode')
  songs = kodi.GetSongs()

  if 'result' in songs and 'songs' in songs['result']:
    songs_array = []

    for song in songs['result']['songs']:
      songs_array.append(song['songid'])

    kodi.Stop()
    kodi.ClearAudioPlaylist()
    kodi.AddSongsToPlaylist(songs_array, True)
    kodi.StartAudioPlaylist()
    response_text = render_template('playing_party')
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the StartOver intent.
@ask.intent('StartOver')
def alexa_start_over():
  card_title = render_template('playing_same')
  print card_title

  kodi.PlayStartOver()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the Skip intent.
@ask.intent('Skip')
def alexa_skip():
  card_title = render_template('playing_next')
  print card_title

  kodi.PlaySkip()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the Prev intent.
@ask.intent('Prev')
def alexa_prev():
  card_title = render_template('playing_previous')
  print card_title

  kodi.PlayPrev()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the Fullscreen intent.
@ask.intent('Fullscreen')
def alexa_fullscreen():
  card_title = render_template('toggle_fullscreen')
  print card_title

  kodi.ToggleFullscreen()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the Mute intent.
@ask.intent('Mute')
def alexa_mute():
  card_title = render_template('mute_unmute')
  print card_title

  kodi.ToggleMute()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the VolumeUp intent.
@ask.intent('VolumeUp')
def alexa_volume_up():
  card_title = render_template('volume_up')
  print card_title

  vol = kodi.VolumeUp()['result']
  response_text = render_template('volume_set', num=vol)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the VolumeDown intent.
@ask.intent('VolumeDown')
def alexa_volume_down():
  card_title = render_template('volume_down')
  print card_title

  vol = kodi.VolumeDown()['result']
  response_text = render_template('volume_set', num=vol)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the VolumeSet intent.
@ask.intent('VolumeSet')
def alexa_volume_set(Volume):
  card_title = render_template('adjusting_volume')
  print card_title

  vol = kodi.VolumeSet(int(Volume), False)['result']
  response_text = render_template('volume_set', num=vol)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the VolumeSetPct intent.
@ask.intent('VolumeSetPct')
def alexa_volume_set_pct(Volume):
  card_title = render_template('adjusting_volume')
  print card_title

  vol = kodi.VolumeSet(int(Volume))['result']
  response_text = render_template('volume_set', num=vol)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the SubtitlesOn intent.
@ask.intent('SubtitlesOn')
def alexa_subtitles_on():
  card_title = render_template('subtitles_enable')
  print card_title

  kodi.SubtitlesOn()
  response_text = kodi.GetCurrentSubtitles()

  return statement(response_text).simple_card(card_title, response_text)


# Handle the SubtitlesOff intent.
@ask.intent('SubtitlesOff')
def alexa_subtitles_off():
  card_title = render_template('subtitles_disable')
  print card_title

  kodi.SubtitlesOff()
  response_text = kodi.GetCurrentSubtitles()

  return statement(response_text).simple_card(card_title, response_text)


# Handle the SubtitlesNext intent.
@ask.intent('SubtitlesNext')
def alexa_subtitles_next():
  card_title = render_template('subtitles_next')
  print card_title

  kodi.SubtitlesNext()
  response_text = kodi.GetCurrentSubtitles()

  return statement(response_text).simple_card(card_title, response_text)


# Handle the SubtitlesPrevious intent.
@ask.intent('SubtitlesPrevious')
def alexa_subtitles_previous():
  card_title = render_template('subtitles_previous')
  print card_title

  kodi.SubtitlesPrevious()
  response_text = kodi.GetCurrentSubtitles()

  return statement(response_text).simple_card(card_title, response_text)


# Handle the AudioStreamNext intent.
@ask.intent('AudioStreamNext')
def alexa_audiostream_next():
  card_title = render_template('audio_stream_next')
  print card_title

  kodi.AudioStreamNext()
  response_text = kodi.GetCurrentAudioStream()

  return statement(response_text).simple_card(card_title, response_text)


# Handle the AudioStreamPrevious intent.
@ask.intent('AudioStreamPrevious')
def alexa_audiostream_previous():
  card_title = render_template('audio_stream_previous')
  print card_title

  kodi.AudioStreamPrevious()
  response_text = kodi.GetCurrentAudioStream()

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerMoveUp intent.
@ask.intent('PlayerMoveUp')
def alexa_player_move_up():
  card_title = render_template('player_move_up')
  print card_title

  kodi.PlayerMoveUp()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerMoveDown intent.
@ask.intent('PlayerMoveDown')
def alexa_player_move_down():
  card_title = render_template('player_move_down')
  print card_title

  kodi.PlayerMoveDown()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerMoveLeft intent.
@ask.intent('PlayerMoveLeft')
def alexa_player_move_left():
  card_title = render_template('player_move_left')
  print card_title

  kodi.PlayerMoveLeft()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerMoveRight intent.
@ask.intent('PlayerMoveRight')
def alexa_player_move_right():
  card_title = render_template('player_move_right')
  print card_title

  kodi.PlayerMoveRight()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerRotateClockwise intent.
@ask.intent('PlayerRotateClockwise')
def alexa_player_rotate_clockwise():
  card_title = render_template('player_rotate')
  print card_title

  kodi.PlayerRotateClockwise()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerRotateCounterClockwise intent.
@ask.intent('PlayerRotateCounterClockwise')
def alexa_player_rotate_counterclockwise():
  card_title = render_template('player_rotate_cc')
  print card_title

  kodi.PlayerRotateCounterClockwise()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomHold intent.
@ask.intent('PlayerZoomHold')
def alexa_player_zoom_hold():
  card_title = render_template('player_zoom_hold')
  print card_title

  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomIn intent.
@ask.intent('PlayerZoomIn')
def alexa_player_zoom_in():
  card_title = render_template('player_zoom_in')
  print card_title

  kodi.PlayerZoomIn()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomInMoveUp intent.
@ask.intent('PlayerZoomInMoveUp')
def alexa_player_zoom_in_move_up():
  card_title = render_template('player_zoom_in_up')
  print card_title

  kodi.PlayerZoomIn()
  kodi.PlayerMoveUp()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomInMoveDown intent.
@ask.intent('PlayerZoomInMoveDown')
def alexa_player_zoom_in_move_down():
  card_title = render_template('player_zoom_in_down')

  kodi.PlayerZoomIn()
  kodi.PlayerMoveDown()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomInMoveLeft intent.
@ask.intent('PlayerZoomInMoveLeft')
def alexa_player_zoom_in_move_left():
  card_title = render_template('player_zoom_in_left')
  print card_title

  kodi.PlayerZoomIn()
  kodi.PlayerMoveLeft()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomInMoveRight intent.
@ask.intent('PlayerZoomInMoveRight')
def alexa_player_zoom_in_move_right():
  card_title = render_template('player_zoom_in_right')
  print card_title

  kodi.PlayerZoomIn()
  kodi.PlayerMoveRight()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomOut intent.
@ask.intent('PlayerZoomOut')
def alexa_player_zoom_out():
  card_title = render_template('player_zoom_out')
  print card_title

  kodi.PlayerZoomOut()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomOutMoveUp intent.
@ask.intent('PlayerZoomOutMoveUp')
def alexa_player_zoom_out_move_up():
  card_title = render_template('player_zoom_out_up')
  print card_title

  kodi.PlayerZoomOut()
  kodi.PlayerMoveUp()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomOutMoveDown intent.
@ask.intent('PlayerZoomOutMoveDown')
def alexa_player_zoom_out_move_down():
  card_title = render_template('player_zoom_out_down')
  print card_title

  kodi.PlayerZoomOut()
  kodi.PlayerMoveDown()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomOutMoveLeft intent.
@ask.intent('PlayerZoomOutMoveLeft')
def alexa_player_zoom_out_move_left():
  card_title = render_template('player_zoom_out_left')
  print card_title

  kodi.PlayerZoomOut()
  kodi.PlayerMoveLeft()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomOutMoveRight intent.
@ask.intent('PlayerZoomOutMoveRight')
def alexa_player_zoom_out_move_right():
  card_title = render_template('player_zoom_out_right')
  print card_title

  kodi.PlayerZoomOut()
  kodi.PlayerMoveRight()
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the PlayerZoomReset intent.
@ask.intent('PlayerZoomReset')
def alexa_player_zoom_reset():
  card_title = render_template('player_zoom_normal')
  print card_title

  kodi.PlayerZoom(1)
  response_text = ""

  return statement(response_text).simple_card(card_title, response_text)


# Handle the Menu intent.
@ask.intent('Menu')
def alexa_context_menu():
  card_title = 'Navigate: Context Menu'
  print card_title

  session.attributes['navigating'] = True

  kodi.Menu()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Home intent.
@ask.intent('Home')
def alexa_go_home():
  card_title = 'Navigate: Home'
  print card_title

  session.attributes['navigating'] = True

  kodi.Home()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Select intent.
@ask.intent('Select')
def alexa_select():
  card_title = 'Navigate: Select'
  print card_title

  session.attributes['navigating'] = True

  kodi.Select()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the PageUp intent.
@ask.intent('PageUp')
def alexa_pageup():
  card_title = 'Navigate: Page up'
  print card_title

  session.attributes['navigating'] = True

  kodi.PageUp()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the PageDown intent.
@ask.intent('PageDown')
def alexa_pagedown():
  card_title = 'Navigate: Page down'
  print card_title

  session.attributes['navigating'] = True

  kodi.PageDown()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Left intent.
@ask.intent('Left')
def alexa_left():
  card_title = 'Navigate: Left'
  print card_title

  session.attributes['navigating'] = True

  kodi.Left()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Right intent.
@ask.intent('Right')
def alexa_right():
  card_title = 'Navigate: Right'
  print card_title

  session.attributes['navigating'] = True

  kodi.Right()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Up intent.
@ask.intent('Up')
def alexa_up():
  card_title = 'Navigate: Up'
  print card_title

  session.attributes['navigating'] = True

  kodi.Up()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Down intent.
@ask.intent('Down')
def alexa_down():
  card_title = 'Navigate: Down'
  print card_title

  session.attributes['navigating'] = True

  kodi.Down()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Back intent.
@ask.intent('Back')
def alexa_back():
  card_title = 'Navigate: Back'
  print card_title

  session.attributes['navigating'] = True

  kodi.Back()
  response_text = render_template('pause')

  return question(response_text).reprompt(response_text)


# Handle the Hibernate intent.
@ask.intent('Hibernate')
def alexa_hibernate():
  card_title = render_template('hibernating')
  print card_title

  kodi.SystemHibernate()

  return statement(card_title).simple_card(card_title, "")


# Handle the Reboot intent.
@ask.intent('Reboot')
def alexa_reboot():
  card_title = render_template('rebooting')
  print card_title

  kodi.SystemReboot()

  return statement(card_title).simple_card(card_title, "")


# Handle the Shutdown intent.
@ask.intent('Shutdown')
def alexa_shutdown():
  card_title = render_template('shutting_down')
  print card_title

  kodi.SystemShutdown()

  return statement(card_title).simple_card(card_title, "")


# Handle the Suspend intent.
@ask.intent('Suspend')
def alexa_suspend():
  card_title = render_template('suspending_system')
  print card_title

  kodi.SystemSuspend()

  return statement(card_title).simple_card(card_title, "")


# Handle the EjectMedia intent.
@ask.intent('EjectMedia')
def alexa_ejectmedia():
  card_title = render_template('ejecting_media')
  print card_title

  kodi.SystemEjectMedia()

  return statement(card_title).simple_card(card_title, "")


# Handle the CleanVideo intent.
@ask.intent('CleanVideo')
def alexa_clean_video():
  card_title = render_template('clean_video')
  print card_title

  # Use threading to prevent timeouts
  c = Process(target=kodi.CleanVideo)
  c.daemon = True
  c.start()

  time.sleep(2)

  return statement(card_title).simple_card(card_title, "")


# Handle the UpdateVideo intent.
@ask.intent('UpdateVideo')
def alexa_update_video():
  card_title = render_template('update_video')
  print card_title

  kodi.UpdateVideo()

  return statement(card_title).simple_card(card_title, "")


# Handle the CleanAudio intent.
@ask.intent('CleanAudio')
def alexa_clean_audio():
  card_title = render_template('clean_audio')
  print card_title

  # Use threading to prevent timeouts
  c = Process(target=kodi.CleanMusic)
  c.daemon = True
  c.start()

  time.sleep(2)

  return statement(card_title).simple_card(card_title, "")


# Handle the UpdateAudio intent.
@ask.intent('UpdateAudio')
def alexa_update_audio():
  card_title = render_template('update_audio')
  print card_title

  kodi.UpdateMusic()

  return statement(card_title).simple_card(card_title, "")


# Handle the AddonExecute intent.
@ask.intent('AddonExecute')
def alexa_addon_execute(Addon):
  heard_addon = str(Addon).lower().translate(None, string.punctuation)

  card_title = render_template('open_addon')
  print card_title

  for content in ['video', 'audio', 'image', 'executable']:
    addons = kodi.GetAddons(content)
    if 'result' in addons and 'addons' in addons['result']:
      addons_array = addons['result']['addons']

      located = kodi.matchHeard(heard_addon, addons_array, lookingFor='name')

      if located:
        kodi.Home()
        kodi.AddonExecute(located['addonid'])
        response_text = render_template('opening', heard_name=located['name'])
        return statement(response_text).simple_card(card_title, response_text)
      else:
        response_text = render_template('could_not_find_addon', heard_addon=heard_addon)
    else:
      response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)

# Handle the AddonGlobalSearch intent.
@ask.intent('AddonGlobalSearch')
def alexa_addon_globalsearch(Movie, Show, Artist, Album, Song):
  card_title = render_template('search')
  heard_search = ''

  if Movie:
    heard_search = str(Movie).lower().translate(None, string.punctuation)
  elif Show:
    heard_search = str(Show).lower().translate(None, string.punctuation)
  elif Artist:
    heard_search = str(Artist).lower().translate(None, string.punctuation)
  elif Album:
    heard_search = str(Album).lower().translate(None, string.punctuation)
  elif Song:
    heard_search = str(Song).lower().translate(None, string.punctuation)

  if (len(heard_search) > 0):
    response_text = render_template('searching', heard_name=heard_search)

    kodi.Home()
    kodi.AddonGlobalSearch(heard_search)
  else:
    response_text = render_template('could_not_find_generic')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchRandomMovie intent.
@ask.intent('WatchRandomMovie')
def alexa_watch_random_movie(Genre):
  genre_located = None
  # If a genre has been specified, match the genre for use in selecting a random film
  if Genre:
    heard_genre = str(Genre).lower().translate(None, string.punctuation)
    card_title = render_template('playing_random_movie_genre', genre=heard_genre)
    genres = kodi.GetMovieGenres()
    if 'result' in genres and 'genres' in genres['result']:
      genres_list = genres['result']['genres']
      genre_located = kodi.matchHeard(heard_genre, genres_list, 'label')
  else:
    card_title = render_template('playing_random_movie')
  print card_title

  # Select from specified genre if one was matched
  if genre_located:
    movies_array = kodi.GetUnwatchedMoviesByGenre(genre_located['label'])
  else:
    movies_array = kodi.GetUnwatchedMovies()
  if not len(movies_array):
    # Fall back to all movies if no unwatched available
    if genre_located:
      movies = kodi.GetMoviesByGenre(genre_located['label'])
    else:
      movies = kodi.GetMovies()
    if 'result' in movies and 'movies' in movies['result']:
      movies_array = movies['result']['movies']

  if len(movies_array):
    random_movie = random.choice(movies_array)

    kodi.PlayMovie(random_movie['movieid'], False)
    if genre_located:
      response_text = render_template('playing_genre', genre=genre_located['label'], movie_name=random_movie['label'])
    else:
      response_text = render_template('playing', heard_name=random_movie['label'])
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchMovie intent.
@ask.intent('WatchMovie')
def alexa_watch_movie(Movie):
  heard_movie = str(Movie).lower().translate(None, string.punctuation)

  card_title = render_template('playing_movie')
  print card_title

  movies = kodi.GetMovies()
  if 'result' in movies and 'movies' in movies['result']:
    movies_array = movies['result']['movies']

    located = kodi.matchHeard(heard_movie, movies_array)

    if located:
      if kodi.GetMovieDetails(located['movieid'])['resume']['position'] > 0:
        action = render_template('resuming_empty')
      else:
        action = render_template('playing_empty')

      kodi.PlayMovie(located['movieid'])

      response_text = render_template('playing_action', action=action, movie_name=heard_movie)
    else:
      response_text = render_template('could_not_find_movie', heard_movie=heard_movie)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchRandomEpisode intent.
@ask.intent('WatchRandomEpisode')
def alexa_watch_random_episode(Show):
  heard_show = str(Show).lower().translate(None, string.punctuation)

  card_title = render_template('playing_random_episode', heard_show=heard_show)
  print card_title

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episodes_result = kodi.GetUnwatchedEpisodesFromShow(located['tvshowid'])

      if not 'episodes' in episodes_result['result']:
        # Fall back to all episodes if no unwatched available
        episodes_result = kodi.GetEpisodesFromShow(located['tvshowid'])

      episodes_array = []

      for episode in episodes_result['result']['episodes']:
        episodes_array.append(episode['episodeid'])

      episode_id = random.choice(episodes_array)
      episode_details = kodi.GetEpisodeDetails(episode_id)

      kodi.PlayEpisode(episode_id, False)

      response_text = render_template('playing_episode_number', season=episode_details['season'], episode=episode_details['episode'], show_name=heard_show)
    else:
      response_text = render_template('could_not_find_show', heard_show=heard_show)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchEpisode intent.
@ask.intent('WatchEpisode')
def alexa_watch_episode(Show, Season, Episode):
  heard_show = str(Show).lower().translate(None, string.punctuation)

  card_title = render_template('playing_an_episode', heard_show=heard_show)
  print card_title

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    heard_season = Season
    heard_episode = Episode

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episode_id = kodi.GetSpecificEpisode(located['tvshowid'], heard_season, heard_episode)

      if episode_id:
        if kodi.GetEpisodeDetails(episode_id)['resume']['position'] > 0:
          action = render_template('resuming_empty')
        else:
          action = render_template('playing_empty')

        kodi.PlayEpisode(episode_id)

        response_text = render_template('playing_action_episode_number', action=action, season=heard_season, episode=heard_episode, show_name=heard_show)

      else:
        response_text = render_template('could_not_find_episode_show', season=heard_season, episode=heard_episode, show_name=heard_show)
    else:
      response_text = render_template('could_not_find_show', heard_show=heard_show)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchNextEpisode intent.
@ask.intent('WatchNextEpisode')
def alexa_watch_next_episode(Show):
  heard_show = str(Show).lower().translate(None, string.punctuation)

  card_title = render_template('playing_next_unwatched_episode', heard_show=heard_show)
  print card_title

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      next_episode_id = kodi.GetNextUnwatchedEpisode(located['tvshowid'])

      if next_episode_id:
        episode_details = kodi.GetEpisodeDetails(next_episode_id)

        if episode_details['resume']['position'] > 0:
          action = render_template('resuming_empty')
        else:
          action = render_template('playing_empty')

        kodi.PlayEpisode(next_episode_id)

        response_text = render_template('playing_action_episode_number', action=action, season=episode_details['season'], episode=episode_details['episode'], show_name=heard_show)
      else:
        response_text = render_template('no_new_episodes_show', show_name=heard_show)
    else:
      response_text = render_template('could_not_find_show', heard_show=heard_show)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchLatestEpisode intent.
@ask.intent('WatchLatestEpisode')
def alexa_watch_newest_episode(Show):
  heard_show = str(Show).lower().translate(None, string.punctuation)

  card_title = render_template('playing_newest_episode', heard_show=heard_show)
  print card_title

  shows = kodi.GetTvShows()
  if 'result' in shows and 'tvshows' in shows['result']:
    shows_array = shows['result']['tvshows']

    located = kodi.matchHeard(heard_show, shows_array)

    if located:
      episode_id = kodi.GetNewestEpisodeFromShow(located['tvshowid'])

      if episode_id:
        episode_details = kodi.GetEpisodeDetails(episode_id)

        if episode_details['resume']['position'] > 0:
          action = render_template('resuming_empty')
        else:
          action = render_template('playing_empty')

        kodi.PlayEpisode(episode_id)

        response_text = render_template('playing_action_episode_number', action=action, season=episode_details['season'], episode=episode_details['episode'], show_name=heard_show)
      else:
        response_text = render_template('no_new_episodes_show', show_name=heard_show)
    else:
      response_text = render_template('could_not_find_show', heard_show=heard_show)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchLastShow intent.
@ask.intent('WatchLastShow')
def alexa_watch_last_show():
  card_title = render_template('last_unwatched')
  print card_title

  last_show_obj = kodi.GetLastWatchedShow()

  try:
    last_show_id = last_show_obj['result']['episodes'][0]['tvshowid']
    next_episode_id = kodi.GetNextUnwatchedEpisode(last_show_id)

    if next_episode_id:
      episode_details = kodi.GetEpisodeDetails(next_episode_id)

      if episode_details['resume']['position'] > 0:
        action = render_template('resuming_empty')
      else:
        action = render_template('playing_empty')

      kodi.PlayEpisode(next_episode_id)

      response_text = render_template('playing_action_episode_number', action=action, season=episode_details['season'], episode=episode_details['episode'], show_name=last_show_obj['result']['episodes'][0]['showtitle'])
    else:
      response_text = render_template('no_new_episodes_show', show_name=last_show_obj['result']['episodes'][0]['showtitle'])
  except:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WatchVideoPlaylist intent.
@ask.intent('WatchVideoPlaylist')
def alexa_watch_video_playlist(VideoPlaylist, shuffle=False):
  heard_search = str(VideoPlaylist).lower().translate(None, string.punctuation)

  if shuffle:
    op = render_template('shuffling_empty')
  else:
    op = render_template('playing_empty')

  card_title = render_template('playing_playlist_action', action=op, playlist_name=heard_search)
  print card_title

  playlist = kodi.FindVideoPlaylist(heard_search)
  if playlist:
    if shuffle:
      videos = kodi.GetPlaylistItems(playlist)['result']['files']

      videos_array = []

      for video in videos:
        videos_array.append(video['file'])

      kodi.Stop()
      kodi.ClearVideoPlaylist()
      kodi.AddVideosToPlaylist(videos_array, True)
      kodi.StartVideoPlaylist()
    else:
      kodi.Stop()
      kodi.StartVideoPlaylist(playlist)
    response_text = render_template('playing_playlist_action', action=op, playlist_name=heard_search)
  else:
    response_text = render_template('could_not_find_playlist', heard_name=heard_search)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the ShuffleVideoPlaylist intent.
@ask.intent('ShuffleVideoPlaylist')
def alexa_shuffle_video_playlist(VideoPlaylist):
  return alexa_watch_video_playlist(VideoPlaylist, True)


# Handle the ShufflePlaylist intent.
@ask.intent('ShufflePlaylist')
def alexa_shuffle_playlist(VideoPlaylist, AudioPlaylist):
  heard_search = ''
  if VideoPlaylist:
    heard_search = str(VideoPlaylist).lower().translate(None, string.punctuation)
  elif AudioPlaylist:
    heard_search = str(AudioPlaylist).lower().translate(None, string.punctuation)

  card_title = render_template('shuffling_playlist', playlist_name=heard_search)
  print card_title

  if (len(heard_search) > 0):
    playlist = kodi.FindVideoPlaylist(heard_search)
    if playlist:
      videos = kodi.GetPlaylistItems(playlist)['result']['files']

      videos_array = []

      for video in videos:
        videos_array.append(video['file'])

      kodi.Stop()
      kodi.ClearVideoPlaylist()
      kodi.AddVideosToPlaylist(videos_array, True)
      kodi.StartVideoPlaylist()
      response_text = render_template('shuffling_playlist_video', playlist_name=heard_search)
    else:
      playlist = kodi.FindAudioPlaylist(heard_search)
      if playlist:
        songs = kodi.GetPlaylistItems(playlist)['result']['files']

        songs_array = []

        for song in songs:
          songs_array.append(song['id'])

        kodi.Stop()
        kodi.ClearAudioPlaylist()
        kodi.AddSongsToPlaylist(songs_array, True)
        kodi.StartAudioPlaylist()
        response_text = render_template('shuffling_playlist_audio', playlist_name=heard_search)

    if not playlist:
      response_text = render_template('could_not_find_playlist', heard_name=heard_search)
  else:
    response_text = render_template('error_parsing_results')

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WhatNewAlbums intent.
@ask.intent('WhatNewAlbums')
def alexa_what_new_albums():
  card_title = render_template('newly_added_albums')
  print card_title

  # Get the list of recently added albums from Kodi
  new_albums = kodi.GetRecentlyAddedAlbums()['result']['albums']

  new_album_names = list(set([kodi.sanitize_name('%s by %s' % (x['label'], x['artist'][0])) for x in new_albums]))
  num_albums = len(new_album_names)

  if num_albums == 0:
    # There's been nothing added to Kodi recently
    response_text = render_template('no_new_albums')
  else:
    random.shuffle(new_album_names)
    limited_new_album_names = new_album_names[0:5]
    album_list = limited_new_album_names[0]
    for one_album in limited_new_album_names[1:-1]:
      album_list += render_template('and') + one_album
    if num_albums > 5:
      album_list += render_template('and') + limited_new_album_names[-1] + render_template('and_more')
    else:
      album_list += render_template('and') + limited_new_album_names[-1]
    response_text = render_template('you_have_list', list=album_list)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WhatNewMovies intent.
@ask.intent('WhatNewMovies')
def alexa_what_new_movies(Genre):
  genre_located = None
  # If a genre has been specified, match the genre for use in selecting random films
  if Genre:
    heard_genre = str(Genre).lower().translate(None, string.punctuation)
    card_title = render_template('newly_added_movies_genre', genre=heard_genre)
    genres = kodi.GetMovieGenres()
    if 'result' in genres and 'genres' in genres['result']:
      genres_list = genres['result']['genres']
      genre_located = kodi.matchHeard(heard_genre, genres_list, 'label')
  else:
    card_title = render_template('newly_added_movies')
  print card_title

  # Select from specified genre if one was matched
  if genre_located:
    new_movies = kodi.GetUnwatchedMoviesByGenre(genre_located['label'])
  else:
    new_movies = kodi.GetUnwatchedMovies()

  new_movie_names = list(set([kodi.sanitize_name(x['title']) for x in new_movies]))
  num_movies = len(new_movie_names)

  if num_movies == 0:
    # There's been nothing added to Kodi recently
    response_text = render_template('no_new_movies')
  else:
    random.shuffle(new_movie_names)
    limited_new_movie_names = new_movie_names[0:5]
    movie_list = limited_new_movie_names[0]
    for one_movie in limited_new_movie_names[1:-1]:
      movie_list += render_template('and') + one_movie
    if num_movies > 5:
      movie_list += render_template('and') + limited_new_movie_names[-1] + render_template('and_more')
    else:
      movie_list += render_template('and') + limited_new_movie_names[-1]
    response_text = render_template('you_have_list', list=movie_list)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WhatNewShows intent.
@ask.intent('WhatNewShows')
def alexa_what_new_episodes():
  card_title = render_template('newly_added_shows')
  print card_title

  # Lists the shows that have had new episodes added to Kodi in the last 5 days

  # Get the list of unwatched EPISODES from Kodi
  new_episodes = kodi.GetUnwatchedEpisodes()

  # Find out how many EPISODES were recently added and get the names of the SHOWS
  new_show_names = list(set([kodi.sanitize_name(x['show']) for x in new_episodes]))
  num_shows = len(new_show_names)

  if num_shows == 0:
    # There's been nothing added to Kodi recently
    response_text = render_template('no_new_shows')
  elif len(new_show_names) == 1:
    # There's only one new show, so provide information about the number of episodes, too.
    count = len(new_episodes)
    if count == 1:
      response_text = render_template('one_new_episode', show_name=new_show_names[0])
    elif count == 2:
      response_text = render_template('two_new_episodes', show_name=new_show_names[0])
    else:
      response_text = render_template('multiple_new_episodes', show_name=new_show_names[0], count=count)
  else:
    # More than one new show has new episodes ready
    random.shuffle(new_show_names)
    limited_new_show_names = new_show_names[0:5]
    show_list = limited_new_show_names[0]
    for one_show in limited_new_show_names[1:-1]:
      show_list += render_template('and') + one_show
    if num_shows > 5:
      show_list += render_template('and') + limited_new_show_names[-1] + render_template('and_more')
    else:
      show_list += render_template('and') + limited_new_show_names[-1]
    response_text = render_template('you_have_episode_list', list=show_list)

  return statement(response_text).simple_card(card_title, response_text)


# Handle the WhatAlbums intent.
@ask.intent('WhatAlbums')
def alexa_what_albums(Artist):
  heard_artist = str(Artist).lower().translate(None, string.punctuation)

  card_title = render_template('albums_by', heard_artist=heard_artist)
  print card_title

  artists = kodi.GetMusicArtists()
  if 'result' in artists and 'artists' in artists['result']:
    artists_list = artists['result']['artists']
    located = kodi.matchHeard(heard_artist, artists_list, 'artist')

    if located:
      albums_result = kodi.GetArtistAlbums(located['artistid'])
      albums = albums_result['result']['albums']
      num_albums = len(albums)

      if num_albums > 0:
        really_albums = list(set([kodi.sanitize_name(x['label']) for x in albums]))
        album_list = really_albums[0]
        if num_albums > 1:
          for one_album in really_albums[1:-1]:
            album_list += render_template('and') + one_album
          album_list += render_template('and') + really_albums[-1]
        response_text = render_template('you_have_list', list=album_list)
      else:
        response_text = render_template('no_albums_artist', artist=heard_artist)
    else:
      response_text = render_template('could_not_find', heard_name=heard_artist)
  else:
    response_text = render_template('could_not_find', heard_name=heard_artist)

  return statement(response_text).simple_card(card_title, response_text)


# What should the Echo say when you just open your app instead of invoking an intent?
@ask.launch
def prepare_help_message():
  response_text = render_template('help')
  card_title = render_template('help_card')

  return statement(response_text).simple_card(card_title, response_text)


@ask.session_ended
def session_ended():
  return "", 200


# End of intent methods