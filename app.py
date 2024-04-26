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
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app,db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String()))
    address = db.Column(db.String(120))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref="venue", lazy=True)

    def __repr__(self):
        return f'<Venue {self.name}>'


class Artist(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.ARRAY(db.String))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref="artist", lazy=True)

    def __repr__(self):
        return f'<Artist {self.name}>'


class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Show {self.artist_id}{self.venue_id}>'


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
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
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


@app.route('/venues/search', methods=['POST'])
def search_venues():
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


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # query the db with the given id
  venue = Venue.query.get(venue_id)

  # Get upcoming and past shows for the venue
  past_shows = []
  upcoming_shows = []
  for show in venue.shows:
     show_data = {
        "artist_id": show.artist_id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
     }
     if show.start_time > datetime.now():
        upcoming_shows.append(show_data)
     else:
        past_shows.append(show_data)

   # Make venue data
  data = {
  "id": venue.id,
  "name": venue.name,
  "genres": venue.genres,
  "address": venue.address,
  "city": venue.city,
  "state": venue.state,
  "phone": venue.phone,
  "website": venue.website,
  "facebook_link": venue.facebook_link,
  "seeking_talent": venue.seeking_talent,
  "seeking_description": venue.seeking_description,
  "image_link": venue.image_link,
  "past_shows": past_shows,
  "upcoming_shows": upcoming_shows,
  "past_shows_count": len(past_shows),
  "upcoming_shows_count": len(upcoming_shows)
  }  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
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
  except Exception as e:
    error = True
    print(e)
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Venue ' + new_venue.name + ' could not be listed.')
  else:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')

  return render_template('pages/home.html')  
  
# Frontend will send a DELETE request using async/await (promise)
@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  venue = Venue.query.get(venue_id)
  if venue:
      db.session.delete(venue)
      db.session.commit()
      print("Deleted: " + venue.name)
      return jsonify({'message': 'Venue deleted successfully'}), 200
  else:
     return jsonify({'error': 'Venue not found'}), 404

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()
  data = []

  for artist in artists:
     arist_data = {
        "id": artist.id,
        "name": artist.name
     }
     data.append(arist_data)

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
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

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist_query = db.session.query(Artist).get(artist_id)

  past_shows_query = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).filter(Show.start_time<datetime.now()).all()
  past_shows = []

  for show in past_shows_query:
    past_shows.append({
      "venue_id": show.venue_id,
      "venue_name": show.venue.name,
      "artist_image_link": show.venue.image_link,
      "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
    })

  upcoming_shows_query = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).filter(Show.start_time>datetime.now()).all()
  upcoming_shows = []

  for show in upcoming_shows_query:
    upcoming_shows.append({
      "venue_id": show.venue_id,
      "venue_name": show.venue.name,
      "artist_image_link": show.venue.image_link,
      "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
    })


  data = {
    "id": artist_query.id,
    "name": artist_query.name,
    "genres": artist_query.genres,
    "city": artist_query.city,
    "state": artist_query.state,
    "phone": artist_query.phone,
    "website": artist_query.website,
    "facebook_link": artist_query.facebook_link,
    "seeking_venue": artist_query.seeking_venue,
    "seeking_description": artist_query.seeking_description,
    "image_link": artist_query.image_link,
    "past_shows": past_shows,
    "upcoming_shows": upcoming_shows,
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)

    # If artist found put it in the form for the user to easily edit
    if artist:
        form = ArtistForm(obj=artist)

    return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
   venue = Venue.query.get(venue_id)
   form = VenueForm(obj=venue)

   return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # get form data and query db
  form_data = request.form
  venue = Venue.query.get(venue_id)

  # Update attributes
  venue.name = form_data['name']
  venue.city = form_data['city']
  venue.state = form_data['state']
  venue.address = form_data['address']
  venue.phone = form_data['phone']
  venue.genres = form_data.getlist('genres')
  venue.facebook_link = form_data['facebook_link']
  venue.image_link = form_data['image_link']
  venue.website_link = form_data['website_link']
  venue.seeking_talent = form_data.get('seeking_talent') == 'y'
  venue.seeking_description = form_data['seeking_description']
  
  db.session.commit()


  return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
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
  except Exception as e:
    error = True
    print(e)
    db.session.rollback()
  finally:
    db.session.close()

  if error:
     flash('An error occurred. Artist ' + new_artist.name + ' could not be listed.')
  else:
     flash('Artist ' + request.form['name'] + ' was successfully listed!')
    
  return render_template('pages/home.html')

  


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
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
        "artist_id": show.artist_name,
        "artist_name": show.artist_name,
        "artist_image_link": show.artist_image_link,
        "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
     }
     data.append(show_data)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False
  try:
    # Create new Venue object with form data
    new_show = Show(
        artist_id=request.form.get('artist_id'),
        venue_id=request.form.get('venue_id'),
        start_time=request.form.get('start_time'),
        )
    db.session.add(new_show)
    db.session.commit()
  except Exception as e:
    error = True
    print(e)
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Show could not be listed.')
  else:
    flash('Show was successfully listed!')

  return render_template('pages/home.html')  

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

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
