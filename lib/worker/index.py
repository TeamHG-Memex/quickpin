''' Worker functions for performing indexing tasks asynchronously. '''

import app.index
from model import Profile
import worker


def index_profile(profile_id):
    ''' Index a profile. '''

    session = worker.get_session()
    solr = worker.get_solr()

    profile = session.query(Profile).filter(Profile.id == profile_id).one()
    solr.add(app.index.make_profile_doc((profile)))
    solr.commit()
