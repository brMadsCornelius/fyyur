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
        # Assuming that the highest id = newest (could create a timestamp in db and save it on creation)
        recentlyCreatedVenues = db.session.query(Venue).order_by(Venue.id.desc()).limit(10).all()
        recentlyCreatedArtists = db.session.query(Artist).order_by(Artist.id.desc()).limit(10).all()

        # Create a list with dictionaries for 10 recent artist names and venue names
        recentVenues = [{'name': venue.name} for venue in recentlyCreatedVenues]
        recentArtists = [{'name': artist.name} for artist in recentlyCreatedArtists]

        return render_template('pages/home.html', recentVenues=recentVenues, recentArtists=recentArtists)
    finally:
        db.session.close()



#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    
    try:
      # Query all cities and states (distinc to get unique)
      cities_and_states = db.session.query(Venue.city, Venue.state).distinct().all()
      data = []

      for city, state in cities_and_states:
          venues_in_city = db.session.query(Venue).filter_by(city=city, state=state).all()

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
      search_result = db.session.query(Venue).filter(Venue.name.ilike(f"%{search_term}%")).all()

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
        venue = db.session.query(Venue).get_or_404(venue_id)

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

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form, meta={'csrf': False})  # Create form object with form data
    
    if form.validate():  # Validate the form
        try:
            # Create new Venue object with form data
            new_venue = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                genres=form.genres.data,
                facebook_link=form.facebook_link.data,
                image_link=form.image_link.data,
                website=form.website_link.data,
                seeking_talent=form.seeking_talent.data == 'y',  
                seeking_description=form.seeking_description.data
            )
            db.session.add(new_venue)
            db.session.commit()
            flash('Venue ' + form.name.data + ' was successfully listed!')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Venue ' + form.name.data + ' could not be listed.')
            print(e)
        finally:
            db.session.remove()

        return redirect(url_for('index'))
    else:
        # If there are validation errors, display them to the user
        error_messages = ", ".join([", ".join(errors) for errors in form.errors.values()])
        flash('Please fix the following errors: ' + error_messages)
        return render_template('forms/new_venue.html', form=form)

  
# Frontend will send a DELETE request using async/await (promise)
@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  
  try:
     venue = db.session.query(Venue).get(venue_id)

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
    search_result = db.session.query(Artist).filter(Artist.name.ilike(f"%{search_term}%")).all()
    
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
        artist = db.session.query(Artist).get_or_404(artist_id)

        past_shows = []
        upcoming_shows = []

        for show in artist.shows:
            venue = show.venue
            show_data = {
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
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


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    try:
      artist = db.session.query(Artist).get(artist_id)

      # If artist found put it in the form for the user to easily edit
      if artist:
          form = ArtistForm(obj=artist)

      return render_template('forms/edit_artist.html', form=form, artist=artist)
    finally:
       db.session.remove()

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  
  try:
    artist = db.session.query(Artist).get(artist_id)

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
    venue = db.session.query(Venue).get(venue_id)
    form = VenueForm(obj=venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)
   finally:
      db.session.remove()

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

  try:
     venue = db.session.query(Venue).get(venue_id)

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
    form = ArtistForm(request.form, meta={'csrf': False})  # Create form object with form data
    
    if form.validate():  # Validate the form
        try:
            # Create new artist object with form data
            new_artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                genres=form.genres.data,
                facebook_link=form.facebook_link.data,
                image_link=form.image_link.data,
                website=form.website_link.data,
                seeking_venue=form.seeking_venue.data == 'y',  
                seeking_description=form.seeking_description.data
            )
            db.session.add(new_artist)
            db.session.commit()
            flash('Artist ' + form.name.data + ' was successfully created!')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Artist ' + form.name.data + ' could not be created.')
            print(e)
        finally:
            db.session.close()

        return redirect(url_for('index'))
    else:
        # If there are validation errors, display them to the user
        error_messages = ", ".join([", ".join(errors) for errors in form.errors.values()])
        flash('Please fix the following errors: ' + error_messages)
        return render_template('forms/new_artist.html', form=form)


  


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
    form = ShowForm(request.form, meta={'csrf': False})  # Create form object with form data
    
    if form.validate():  # Validate the form
        try:
            # Create new show object with form data
            new_show = Show(
                artist_id=form.artist_id.data,
                venue_id=form.venue_id.data,
                start_time=form.start_time.data,
            )
            db.session.add(new_show)
            db.session.commit()
            flash('Show was successfully listed!')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Show could not be listed.')
            print(e)
        finally:
            db.session.close()

        return redirect(url_for('index'))
    else:
        # If there are validation errors, display them to the user
        error_messages = ", ".join([", ".join(errors) for errors in form.errors.values()])
        flash('Please fix the following errors: ' + error_messages)
        return render_template('forms/new_show.html', form=form)


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

