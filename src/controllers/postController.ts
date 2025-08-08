import { Request, Response } from 'express';
import { PostModel } from '../models/post';

export const createPost = async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, content } = req.body;
    
    // Validation
    if (!title || !content) {
      res.status(400).json({
        error: 'Missing required fields',
        required: ['title', 'content']
      });
      return;
    }

    const postData = {
      title,
      content
    };

    const newPost = await PostModel.create(postData);

    res.status(201).json({
      success: true,
      data: newPost
    });
  } catch (error) {
    console.error('Error creating post:', error);
    res.status(500).json({
      error: 'Failed to create post',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const getPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    const posts = await PostModel.findAll();
    res.json({
      success: true,
      data: posts
    });
  } catch (error) {
    console.error('Error fetching posts:', error);
    res.status(500).json({
      error: 'Failed to fetch posts',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const getPostById = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const post = await PostModel.findById(id);
    
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    res.json({
      success: true,
      data: post
    });
  } catch (error) {
    console.error('Error fetching post:', error);
    res.status(500).json({
      error: 'Failed to fetch post',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};