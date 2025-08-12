import express from 'express';
import { createPost, getPosts, getPostById, getMeetups, getGeneralPosts, joinMeetup, leaveMeetup, getParticipants } from '../controllers/postController';
import { createComment, getComments, deleteComment, toggleLike, getLikes, toggleCommentLike, getCommentLikes } from '../controllers/commentController';
import { uploadImage } from '../middleware/upload';
import { authenticateToken, optionalAuth } from '../middleware/auth';

const router = express.Router();

// Main unified endpoints
router.post('/', authenticateToken, uploadImage.single('image'), createPost);         // POST /api/posts
router.get('/', optionalAuth, getPosts);                                        // GET /api/posts?category=수리
router.get('/:id', getPostById);                                  // GET /api/posts/:id

// Meetup participation endpoints
router.post('/:id/join', authenticateToken, joinMeetup);                            // POST /api/posts/:id/join
router.delete('/:id/leave', authenticateToken, leaveMeetup);                        // DELETE /api/posts/:id/leave
router.get('/:id/participants', optionalAuth, getParticipants);                // GET /api/posts/:id/participants

// Comments endpoints
router.post('/:id/comments', authenticateToken, createComment);                     // POST /api/posts/:id/comments (+ parent_comment_id for replies)
router.get('/:id/comments', optionalAuth, getComments);                        // GET /api/posts/:id/comments
router.delete('/:id/comments/:commentId', authenticateToken, deleteComment);        // DELETE /api/posts/:id/comments/:commentId

// Comment likes endpoints
router.post('/:id/comments/:commentId/like', authenticateToken, toggleCommentLike); // POST /api/posts/:id/comments/:commentId/like
router.get('/:id/comments/:commentId/likes', optionalAuth, getCommentLikes);   // GET /api/posts/:id/comments/:commentId/likes

// Post likes endpoints
router.post('/:id/like', authenticateToken, toggleLike);                            // POST /api/posts/:id/like
router.get('/:id/likes', optionalAuth, getLikes);                              // GET /api/posts/:id/likes

// Helper endpoints for convenience  
router.get('/meetups/all', getMeetups);                          // GET /api/posts/meetups/all
router.get('/general/all', getGeneralPosts);                     // GET /api/posts/general/all

export default router;