import express from 'express';
import { createPost, getPosts, getPostById, getMeetups, getGeneralPosts, joinMeetup, leaveMeetup, getParticipants } from '../controllers/postController';
import { uploadImage } from '../middleware/upload';

const router = express.Router();

// Main unified endpoints
router.post('/', uploadImage.single('image'), createPost);         // POST /api/posts
router.get('/', getPosts);                                        // GET /api/posts?category=수리
router.get('/:id', getPostById);                                  // GET /api/posts/:id

// Meetup participation endpoints
router.post('/:id/join', joinMeetup);                            // POST /api/posts/:id/join
router.delete('/:id/leave', leaveMeetup);                        // DELETE /api/posts/:id/leave
router.get('/:id/participants', getParticipants);                // GET /api/posts/:id/participants

// Helper endpoints for convenience  
router.get('/meetups/all', getMeetups);                          // GET /api/posts/meetups/all
router.get('/general/all', getGeneralPosts);                     // GET /api/posts/general/all

export default router;