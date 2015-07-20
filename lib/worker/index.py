''' Worker functions for performing indexing tasks asynchronously. '''

import app.database
import app.index
from model import DarkPost, DarkSite, DarkThread, DarkUser
import worker


def reindex_dark_site(site_id):
    ''' Reindex a DarkSite record and all of its denormalized records. '''

    session = worker.get_session()
    solr = worker.get_solr()

    # Initialize job completion percentage.
    post_query = session.query(DarkPost, DarkSite, DarkThread, DarkUser) \
                        .join(DarkPost.thread) \
                        .join(DarkThread.site) \
                        .join(DarkPost.author) \
                        .filter(DarkSite.id == site_id) \
                        .order_by(DarkPost.id)

    user_query = session.query(DarkUser, DarkSite) \
                        .join(DarkUser.site) \
                        .filter(DarkUser.site_id == site_id) \
                        .order_by(DarkUser.id)

    total_records = 1 + post_query.count() + user_query.count()

    job = worker.get_job()
    job.meta['total'] = total_records
    job.meta['current'] = 0
    job.save()

    # Reindex the site itself.
    site = session.query(DarkSite).filter(DarkSite.id == site_id).one()
    solr.add(app.index.make_dark_site_doc((site)))
    solr.commit()

    job.meta['current'] += 1
    job.save()

    # Reindex the posts related to this site.
    for chunk in app.database.query_chunks(post_query, DarkPost.id):
        docs = list()

        for record in chunk:
            docs.append(app.index.make_dark_post_doc(*record))

        solr.add(docs)
        solr.commit()

        job.meta['current'] += len(docs)
        job.save()

    # Reindex the users related to this site.
    for chunk in app.database.query_chunks(user_query, DarkUser.id):
        docs = list()

        for record in chunk:
            docs.append(app.index.make_dark_user_doc(*record))

        solr.add(docs)
        solr.commit()

        job.meta['current'] += len(docs)
        job.save()

    # Cleanup
    solr.optimize()

    job.meta['current'] = job.meta['total']
    job.save()
