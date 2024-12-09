from apscheduler.job import Job
from apscheduler.jobstores.base import BaseJobStore
from apscheduler.util import maybe_ref
import redis
import pickle
import logging

logger = logging.getLogger(__name__)

class RedisJobStore:
    def __init__(self, host="localhost", port=6379, db=0, password=None):
        self.redis = redis.Redis(host=host, port=port, db=db, password=password)
        logger.info("Connected to Redis.")

    def add_job(self, job_id, job_data):
        try:
            serialized_data = pickle.dumps(job_data)
            self.redis.set(job_id, serialized_data)
            logger.info(f"Added job {job_id} to Redis.")
        except Exception as e:
            logger.error(f"Failed to add job {job_id} to Redis: {e}")

    def get_job(self, job_id):
        try:
            serialized_data = self.redis.get(job_id)
            if serialized_data is None:
                logger.error(f"Job {job_id} not found in Redis.")
                return None
            job = pickle.loads(serialized_data)
            logger.info(f"Loaded job {job_id} from Redis.")
            return job
        except Exception as e:
            logger.error(f"Failed to load job {job_id} from Redis: {e}")
            return None

    def remove_job(self, job_id):
        try:
            self.redis.delete(job_id)
            logger.info(f"Removed job {job_id} from Redis.")
        except Exception as e:
            logger.error(f"Failed to remove job {job_id} from Redis: {e}")

    def get_due_jobs(self, now):
        jobs = []
        for key in self.redis.keys("job:*"):
            job_data = self.redis.get(key)
            try:
                job_state = pickle.loads(job_data)
                job = self._reconstitute_job(job_state)
                if job.next_run_time and job.next_run_time <= now:
                    jobs.append(job)
            except Exception as e:
                logger.error(f"Failed to load job from Redis: {e}")
        return jobs

    def get_all_jobs(self):
        jobs = []
        for key in self.redis.keys("job:*"):
            job_data = self.redis.get(key)
            try:
                job_state = pickle.loads(job_data)
                job = self._reconstitute_job(job_state)
                jobs.append(job)
            except Exception as e:
                logger.error(f"Failed to load job from Redis: {e}")
        return jobs

    def get_next_run_time(self):
        jobs = self.get_all_jobs()
        return min((job.next_run_time for job in jobs), default=None)

    def lookup_job(self, job_id):
        job_key = f"job:{job_id}"
        job_data = self.redis.get(job_key)
        if job_data:
            try:
                job_state = pickle.loads(job_data)
                return self._reconstitute_job(job_state)
            except Exception as e:
                logger.error(f"Failed to lookup job {job_id}: {e}")
        return None

    def update_job(self, job):
        self.add_job(job)

    def remove_all_jobs(self):
        for key in self.redis.keys("job:*"):
            self.redis.delete(key)
        logger.info("Removed all jobs from Redis.")

    def _reconstitute_job(self, job_state):
        """Recreate a job from its serialized state."""
        try:
            job_class = maybe_ref(job_state["job_class"])
            job = job_class.__new__(job_class)
            job.__setstate__(job_state)
            return job
        except Exception as e:
            logger.error(f"Failed to reconstitute job: {e}")
            raise
