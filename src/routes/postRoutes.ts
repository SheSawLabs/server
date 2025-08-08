import express from 'express';
import { createPost, getPosts, getPostById } from '../controllers/postController';

const router = express.Router();

// POST /api/posts - Create a new post
router.post('/', createPost);

// GET /api/posts - Get all posts
router.get('/', getPosts);

// GET /api/posts/:id - Get a specific post
router.get('/:id', getPostById);

export default router;