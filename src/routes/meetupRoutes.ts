import express from 'express';
import { createMeetup, getMeetups, getMeetupById } from '../controllers/meetupController';
import { uploadImage } from '../middleware/upload';

const router = express.Router();

// POST /api/meetups - Create a new meetup
router.post('/', uploadImage.single('image'), createMeetup);

// GET /api/meetups - Get all meetups
router.get('/', getMeetups);

// GET /api/meetups/:id - Get a specific meetup
router.get('/:id', getMeetupById);

export default router;