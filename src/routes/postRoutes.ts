import express from 'express';
import { createPost, getPosts, getPostById, getMeetups, getGeneralPosts, joinMeetup, leaveMeetup, getParticipants } from '../controllers/postController';
import { createComment, getComments, deleteComment, toggleLike, getLikes } from '../controllers/commentController';
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

// Comments endpoints
router.post('/:id/comments', createComment);                     // POST /api/posts/:id/comments
router.get('/:id/comments', getComments);                        // GET /api/posts/:id/comments?user_name=name
router.delete('/:id/comments/:commentId', deleteComment);        // DELETE /api/posts/:id/comments/:commentId

// Likes endpoints
router.post('/:id/like', toggleLike);                            // POST /api/posts/:id/like
router.get('/:id/likes', getLikes);                              // GET /api/posts/:id/likes?user_name=name

// Helper endpoints for convenience  
router.get('/meetups/all', getMeetups);                          // GET /api/posts/meetups/all
router.get('/general/all', getGeneralPosts);                     // GET /api/posts/general/all

export default router;