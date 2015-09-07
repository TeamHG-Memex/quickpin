from flask import g, jsonify
from flask.ext.classy import FlaskView, route
import rq
from rq.exceptions import NoSuchJobError, UnpickleError
from werkzeug.exceptions import NotFound

from app.authorization import login_required
from app.rest import url_for

class TasksView(FlaskView):
    ''' Data about background tasks. '''

    decorators = [login_required]

    @route('/failed/<id_>', methods=['DELETE'])
    def delete(self, id_):
        '''
        Delete a failed task with the given id_.

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query id: the job ID to delete

        :>header Content-Type: application/json

        :status 200: ok
        :status 401: authentication required
        :status 403: you must be an administrator
        :status 404: no job exists with this ID
        '''

        with rq.Connection(g.redis):
            found = False

            for job in rq.get_failed_queue().jobs:
                if job.id == id_:
                    job.delete()
                    found = True
                    break

            if not found:
                raise NotFound('No job exists with ID "%s".' % id_)

        return jsonify(message='ok')

    @route('failed')
    def failed_tasks(self):
        '''
        Get data about failed tasks.

        **Example Response**

        .. sourcecode:: json

            {
                "failed": [
                    {
                        "description": "Doing important stuff...",
                        "exception": "Traceback (most recent call...",
                        "function": "worker.index.reindex_site(1)",
                        "id": "dea6bd20-4f8e-44d2-bee1-b5db78eb4cc8",
                        "original_queue": "index"
                    },
                    ...
                ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json list failed: list of failed tasks
        :>json str failed[n]["description"]: description of the task (optional)
        :>json str failed[n]["exception"]: stack trace of the exception
        :>json str failed[n]["function"]: the function call that was originally
            queued
        :>json str failed[n]["id"]: unique identifier
        :>json str failed[n]["original_queue"]: the queue that this task was
            initially placed on before it failed

        :status 200: ok
        :status 401: authentication required
        :status 403: you must be an administrator
        '''

        failed_tasks = list()

        with rq.Connection(g.redis):
            for failed_task in rq.get_failed_queue().jobs:
                try:
                    if 'description' in failed_task.meta:
                        desc = failed_task.meta['description']
                    else:
                        desc = None

                    failed_tasks.append({
                        'description': desc,
                        'function': failed_task.get_call_string(),
                        'exception': failed_task.exc_info.decode(),
                        'id': failed_task.id,
                        'original_queue': failed_task.origin,
                    })
                except UnpickleError:
                    failed_tasks.append({
                        'description': 'Error: this job cannot be unpickled.',
                        'function': None,
                        'exception': failed_task.exc_info.decode(),
                        'id': failed_task.id,
                        'original_queue': failed_task.origin,
                    })

        return jsonify(failed=failed_tasks)

    @route('queues')
    def queues(self):
        '''
        Get data about message queues.

        **Example Response**

        .. sourcecode:: json

            {
                "queues": [
                    {
                        "name": "default",
                        "pending_tasks": 4
                    },
                    ...
                ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json list queues: list of message queues
        :>json str queues[n]["name"]: name of the message queue
        :>json int queues[n]["pending_tasks"]: number of tasks pending in this
            queue

        :status 200: ok
        :status 401: authentication required
        :status 403: you must be an administrator
        '''

        queues = list()

        with rq.Connection(g.redis):

            for queue in rq.Queue.all():
                if queue.name == 'failed':
                    continue

                queues.append({
                    'pending_tasks': queue.count,
                    'name': queue.name,
                })

        return jsonify(queues=queues)

    @route('workers')
    def workers(self):
        '''
        Get data about workers.

        **Example Response**

        .. sourcecode:: json

            {
                "workers": [
                    {
                        "current_job": null,
                        "name": "ubuntu.50224",
                        "queues": ["default", "index"],
                        "state": "idle"
                    },
                    {
                        "current_job": {
                            "current": 1321,
                            "description": "Running reports.",
                            "id": "cc4618c1-22ed-4b5d-a9b8-5186c0259b46",
                            "progress": 0.4520876112251882,
                            "total": 2922,
                            "type": "index"
                        },
                        "name": "ubuntu.49330",
                        "queues": ["index"],
                        "state": "busy"
                    },
                    ...
                ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json list workers: list of workers
        :>json object workers[n]["current_job"]: the job currently executing on
            this worker, or null if it's not executing any jobs
        :>json int workers[n]["current_job"]["current"]: the number of
            records processed so far by this job
        :>json str workers[n]["current_job"]["description"]: description of
            the current job (optional)
        :>json str workers[n]["current_job"]["id"]: unique job identifier
        :>json float workers[n]["current_job"]["progress"]: the percentage of
            records processed by this job, expressed as a decimal
        :>json int workers[n]["current_job"]["total"]: the total number of
            records expected to be processed by this job
        :>json str workers[n]["current_job"]["type"]: the type of this job,
            indicating what subsystem it belongs to (optional)
        :>json str workers[n]["name"]: name of the worker process
        :>json list workers[n]["queues"]: the name[s] of the queues that this
            worker is listening to
        :>json str workers[n]["state"]: the queue's current state

        :status 200: ok
        :status 401: authentication required
        :status 403: you must be an administrator
        '''

        workers = list()

        with rq.Connection(g.redis):

            for worker in rq.Worker.all():
                state = worker.get_state().decode()
                job_json = None

                if state == 'busy':
                    job = worker.get_current_job()

                    if job is not None:
                        if 'description' in job.meta:
                            description = job.meta['description']
                        else:
                            description = None

                        job_json = {
                            'current': job.meta['current'],
                            'description': description,
                            'id': job.id,
                            'progress': job.meta['current']  / job.meta['total'],
                            'total': job.meta['total'],
                            'type': job.meta['type'] if 'type' in job.meta else None
                        }

                workers.append({
                    'current_job': job_json,
                    'name': worker.name,
                    'state': worker.get_state().decode(),
                    'queues': worker.queue_names(),
                })

        return jsonify(workers=workers)
