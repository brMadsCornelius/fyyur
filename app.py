#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import db, Venue, Artist, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app,db)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  try:
     # Asuming that highest id = newest (could create a timestamp in db and save it on creation)
     recentlyCreatedVenues = Venue.query.order_by(Venue.id.desc()).limit(10).all()
     recentlyCreatedArtists = Artist.query.order_by(Artist.id.desc()).limit(10).all()

    # Create a list with dictonaries for 10 recent artist name and venue name
     recentVenues = [{'name': venue.name} for venue in recentlyCreatedVenues]
     recentArtists = [{'name': artist.name} for artist in recentlyCreatedArtists]

     return render_template('pages/home.html',recentVenues=recentVenues,recentArtists=recentArtists)
  finally:
     db.session.remove()


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    
    try:
      # Query all cities and states (distinc to get unique)
      cities_and_states = db.session.query(Venue.city, Venue.state).distinct().all()
      data = []

      for city, state in cities_and_states:
          venues_in_city = Venue.query.filter_by(city=city, state=state).all()
          venues_data = []

          for venue in venues_in_city:
              # Count the number of upcoming shows for the current venue
              num_upcoming_shows = len([show for show in venue.shows if show.start_time > datetime.now()])
              venue_data = {
                  "id": venue.id,
                  "name": venue.name,
                  "num_upcoming_shows": num_upcoming_shows
              }
              venues_data.append(venue_data)

          city_state_data = {
              "city": city,
              "state": state,
              "venues": venues_data
          }

          data.append(city_state_data)

      return render_template('pages/venues.html', areas=data)
    except Exception as e:
       print(e)
       flash("Unable to query venues in database")
       return render_template('pages/venues.html')
    finally:
       db.session.remove()
       

    


@app.route('/venues/search', methods=['POST'])
def search_venues():
    try:
       
      search_term = request.form.get('search_term', '')

      # use sql LIKE to search
      search_result = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()

      # Prepare response dict for each result. 
      venue_data_list = []
      for venue in search_result:
        venue_data = {
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": len(venue.shows)
        }
        venue_data_list.append(venue_data)

      response = {
        "count": len(venue_data_list),
        "data": venue_data_list
      }

      return render_template('pages/search_venues.html', results=response, search_term=search_term)
    except Exception as e:
       print(e)
    finally:
       db.session.remove()


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    try:
        venue = Venue.query.get_or_404(venue_id)

        past_shows = []
        upcoming_shows = []

        for show in venue.shows:
            temp_show = {
                'artist_id': show.artist_id,
                'artist_name': show.artist.name,
                'artist_image_link': show.artist.image_link,
                'start_time': show.start_time.strftime("%m/%d/%Y, %H:%M")
            }
            if show.start_time <= datetime.now():
                past_shows.append(temp_show)
            else:
                upcoming_shows.append(temp_show)

        data = vars(venue)
        data['past_shows'] = past_shows
        data['upcoming_shows'] = upcoming_shows
        data['past_shows_count'] = len(past_shows)
        data['upcoming_shows_count'] = len(upcoming_shows)

        return render_template('pages/show_venue.html', venue=data)
    except Exception as e:
        flash("An error occurred while processing your request.")
        return render_template('pages/venues.html')
    finally:
       db.session.remove()

  # Old solution not using join (save it if i want to use it in another project)
  # try:
  #   # query the db with the given id
  #   venue = Venue.query.get(venue_id)

  #   if not venue:
  #     flash(f"Can't find venue with id: {venue_id}")
  #     return render_template('pages/venues.html')

  #   # Get upcoming and past shows for the venue
  #   past_shows = []
  #   upcoming_shows = []
  #   for show in venue.shows:
  #     show_data = {
  #         "artist_id": show.artist_id,
  #         "artist_name": show.artist.name,
  #         "artist_image_link": show.artist.image_link,
  #         "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
  #     }
  #     if show.start_time > datetime.now():
  #         upcoming_shows.append(show_data)
  #     else:
  #         past_shows.append(show_data)

  #   # Make venue data in correct format
  #   data = {
  #   "id": venue.id,
  #   "name": venue.name,
  #   "genres": venue.genres,
  #   "address": venue.address,
  #   "city": venue.city,
  #   "state": venue.state,
  #   "phone": venue.phone,
  #   "website": venue.website,
  #   "facebook_link": venue.facebook_link,
  #   "seeking_talent": venue.seeking_talent,
  #   "seeking_description": venue.seeking_description,
  #   "image_link": venue.image_link,
  #   "past_shows": past_shows,
  #   "upcoming_shows": upcoming_shows,
  #   "past_shows_count": len(past_shows),
  #   "upcoming_shows_count": len(upcoming_shows)
  #   }  
  #   return render_template('pages/show_venue.html', venue=data)
  # finally:
  #    db.session.remove()


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  
  try:
    # Create new Venue object with form data
    new_venue = Venue(
        name=request.form.get('name'),
        city=request.form.get('city'),
        state=request.form.get('state'),
        address=request.form.get('address'),
        phone=request.form.get('phone'),
        genres=request.form.getlist('genres'),
        facebook_link=request.form.get('facebook_link'),
        image_link=request.form.get('image_link'),
        website=request.form.get('website_link'),
        seeking_talent=request.form.get('seeking_talent') == 'y',  # 'y' if checked otherwise None.
        seeking_description=request.form.get('seeking_description')
      )
    db.session.add(new_venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    print(e)
  finally:
    db.session.remove()

  return redirect(url_for('index'))  
  
# Frontend will send a DELETE request using async/await (promise)
@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  
  try:
     venue = Venue.query.get(venue_id)

     if not venue:
        flash(f"Venue with ID: {venue_id} not found")
        return jsonify({'message': 'Venue not found'}), 404

     db.session.delete(venue)
     db.session.commit()
     flash(f"Deleted: {venue.name}")
     return jsonify({'message': 'Venue deleted successfully'}), 204
  except Exception as e:
     db.session.rollback()
     flash(f"Couldn't delete: {venue.name}")
     print(e)
     return jsonify({'message': 'An error occurred'}), 500
  finally:
     db.session.remove()


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  try:
     data = db.session.query(Artist).all()
     return render_template('pages/artists.html', artists=data)
  finally:
     db.session.remove()

  


@app.route('/artists/search', methods=['POST'])
def search_artists():
  try:
    search_term = request.form.get('search_term','')
    
    #use sql LIKE to search
    search_result = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()
    
    # Prepare response dict for each result.
    response ={
      "count": len(search_result),
      "data":[{
          "id": artist.id,
          "name": artist.name,
          "num_upcoming_shows": len(artist.shows)
      } for artist in search_result]
    }

    return render_template('pages/search_artists.html', results=response, search_term=search_term)
  finally:
     db.session.remove()


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    try:
        artist = Artist.query.get_or_404(artist_id)

        past_shows = []
        upcoming_shows = []

        for show in artist.shows:
            venue = show.venue
            show_data = {
                "venue_id": venue.id,
                "venue_name": venue.name,
                "artist_image_link": artist.image_link,
                "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            if show.start_time < datetime.now():
                past_shows.append(show_data)
            else:
                upcoming_shows.append(show_data)

        data = {
            "id": artist.id,
            "name": artist.name,
            "genres": artist.genres,
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "website": artist.website,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows_count": len(upcoming_shows)
        }

        return render_template('pages/show_artist.html', artist=data)
    except Exception as e:
        flash("An error occurred while processing your request.")
        return render_template('pages/artists.html')
    finally:
        db.session.remove()



# Old controller before reviews from udacity
# @app.route('/artists/<int:artist_id>')
# def show_artist(artist_id):
#   try:
#     artist_query = db.session.query(Artist).get(artist_id)

#     past_shows_query = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).filter(Show.start_time<datetime.now()).all()
#     past_shows = []

#     for show in past_shows_query:
#       past_shows.append({
#         "venue_id": show.venue_id,
#         "venue_name": show.venue.name,
#         "artist_image_link": show.venue.image_link,
#         "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
#       })

#     upcoming_shows_query = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).filter(Show.start_time>datetime.now()).all()
#     upcoming_shows = []

#     for show in upcoming_shows_query:
#       upcoming_shows.append({
#         "venue_id": show.venue_id,
#         "venue_name": show.venue.name,
#         "artist_image_link": show.venue.image_link,
#         "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
#       })


#     data = {
#       "id": artist_query.id,
#       "name": artist_query.name,
#       "genres": artist_query.genres,
#       "city": artist_query.city,
#       "state": artist_query.state,
#       "phone": artist_query.phone,
#       "website": artist_query.website,
#       "facebook_link": artist_query.facebook_link,
#       "seeking_venue": artist_query.seeking_venue,
#       "seeking_description": artist_query.seeking_description,
#       "image_link": artist_query.image_link,
#       "past_shows": past_shows,
#       "upcoming_shows": upcoming_shows,
#       "past_shows_count": len(past_shows),
#       "upcoming_shows_count": len(upcoming_shows),
#     }

#     return render_template('pages/show_artist.html', artist=data)
#   finally:
#      db.session.remove()

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    try:
      artist = Artist.query.get(artist_id)

      # If artist found put it in the form for the user to easily edit
      if artist:
          form = ArtistForm(obj=artist)

      return render_template('forms/edit_artist.html', form=form, artist=artist)
    finally:
       db.session.remove()

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  
  try:
    artist = Artist.query.get(artist_id)

    if not artist:
      flash('Artist not found.')
      return redirect(url_for('show_artist', artist_id=artist_id))

    artist.name = request.form.get('name')
    artist.city = request.form.get('city')
    artist.state = request.form.get('state')
    artist.phone = request.form.get('phone')
    artist.genres = request.form.getlist('genres')
    artist.image_link = request.form.get('image_link')
    artist.facebook_link = request.form.get('facebook_link')
    artist.website = request.form.get('website')
    artist.seeking_venue = request.form.get('seeking_venue') == 'y' # y if chekced otherwise none
    artist.seeking_description = request.form.get('seeking_description')

    db.session.commit()
    flash(f"Artist: {artist.name} was successfully updated!")
  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Artist could not be changed.')
    print(e)
  finally: 
    db.session.remove()

  return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
   try:
    venue = Venue.query.get(venue_id)
    form = VenueForm(obj=venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)
   finally:
      db.session.remove()

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

  try:
     venue = Venue.query.get(venue_id)

     if not venue:
        flash("Venue not found!")
        return redirect(url_for('show_venue', venue_id=venue_id))
     
    # Update attributes
     venue.name = request.form.get('name')
     venue.city = request.form.get('city')
     venue.state = request.form.get('state')
     venue.address = request.form.get('address')
     venue.phone = request.form.get('phone')
     venue.genres = request.form.getlist('genres')
     venue.facebook_link = request.form.get('facebook_link')
     venue.image_link = request.form.get('image_link')
     venue.website_link = request.form.get('website_link')
     venue.seeking_talent = request.form.get('seeking_talent') == 'y' # y if checked otherwise none
     venue.seeking_description = request.form.get('seeking_description')

     db.session.commit()
     flash(f"Venue: {venue.name} was successfully updated!")
  except Exception as e:
     db.session.rollback()
     flash("An error occured. Venue could not be changed!")
     print(e)
  finally:
     db.session.remove()

  return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

  try:
    # Create new artist object with form data
    new_artist = Artist(
        name=request.form.get('name'),
        city=request.form.get('city'),
        state=request.form.get('state'),
        phone=request.form.get('phone'),
        genres=request.form.getlist('genres'),
        facebook_link=request.form.get('facebook_link'),
        image_link=request.form.get('image_link'),
        website=request.form.get('website_link'),
        seeking_venue=request.form.get('seeking_venue') == 'y',  # 'y' if checked otherwise None.
        seeking_description=request.form.get('seeking_description')
      )
    db.session.add(new_artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully created!')
  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be created.')
    print(e)
  finally:
    db.session.remove()
    
  return redirect(url_for('index'))

  


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  try:
    # Use join query to get shows
    shows = db.session.query(
      Show.venue_id,
      Venue.name.label('venue_name'),
      Show.artist_id,
      Artist.name.label('artist_name'),
      Artist.image_link.label('artist_image_link'),
      Show.start_time
    ).join(Venue, Show.venue_id == Venue.id).join(Artist, Show.artist_id == Artist.id).all()

    # Create a list to store the show data
    data = []
    for show in shows:
      show_data = {
          "venue_id": show.venue_id,
          "venue_name": show.venue_name,
          "artist_id": show.artist_id,
          "artist_name": show.artist_name,
          "artist_image_link": show.artist_image_link,
          "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
      }
      data.append(show_data)

    return render_template('pages/shows.html', shows=data)
  finally:
     db.session.remove()

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  
  try:
    # Create new Venue object with form data
    new_show = Show(
        artist_id=request.form.get('artist_id'),
        venue_id=request.form.get('venue_id'),
        start_time=request.form.get('start_time'),
        )
    db.session.add(new_show)
    db.session.commit()
    flash('Show was successfully listed!')
  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
    print(e)
  finally:
    db.session.remove()

  return redirect(url_for('index'))  

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#


# run app when calling app.py from terminal
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

