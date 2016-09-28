''' Worker functions for performing indexing tasks asynchronously. '''

import app.index
from model import Post, Profile
import worker


def index_posts(post_ids):
    ''' Index a collection of posts. '''

    worker.start_job()
    session = worker.get_session()
    solr = worker.get_solr()

    post_query = session.query(Post, Profile) \
                        .join(Post.author) \
                        .filter(Post.id.in_(post_ids))

    for post, author in post_query:
        solr.add(app.index.make_post_doc(post, author))

    solr.commit()
    worker.finish_job()


def index_profile(profile_id):
    ''' Index a profile. '''

    worker.start_job()
    session = worker.get_session()
    solr = worker.get_solr()

    profile = session.query(Profile).filter(Profile.id == profile_id).one()
    solr.add(app.index.make_profile_doc(profile))
    solr.commit()
    worker.finish_job()


def delete_profile(profile_id):
    ''' Delete a profile. '''

    worker.start_job()
    session = worker.get_session()
    solr = worker.get_solr()
    query = solr.Q(solr.Q(type_s='Profile') & solr.Q(profile_id_i=profile_id))
    solr.delete_by_query(query=query)
    solr.commit()
    worker.finish_job()


def delete_profile_posts(profile_id):
    ''' Delete profile posts. '''

    worker.start_job()
    session = worker.get_session()
    solr = worker.get_solr()
    query = solr.Q(solr.Q(type_s='Post') & solr.Q(profile_id_i=profile_id))
    solr.delete_by_query(query=query)
    solr.commit()
    worker.finish_job()
