import { Request, Response } from 'express';
import { PostModel, PostCategory } from '../models/post';

const VALID_CATEGORIES: PostCategory[] = ['수리', '소분', '취미', '기타', '일반'];

export const createPost = async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, content, category, location, date } = req.body;
    
    // Basic validation
    if (!title || !content || !category) {
      res.status(400).json({
        error: 'Missing required fields',
        required: ['title', 'content', 'category']
      });
      return;
    }

    // Category validation
    if (!VALID_CATEGORIES.includes(category)) {
      res.status(400).json({
        error: 'Invalid category',
        validCategories: VALID_CATEGORIES
      });
      return;
    }

    // Meetup validation (모임 카테고리는 location과 date 필수)
    if (category !== '일반' && (!location || !date)) {
      res.status(400).json({
        error: 'Meetup posts require location and date',
        required: ['location', 'date'],
        message: `Category '${category}' requires location and date fields`
      });
      return;
    }

    // Handle image URL if file was uploaded
    const imageUrl = req.file ? `/uploads/${req.file.filename}` : undefined;

    const postData = {
      title,
      content,
      category,
      image_url: imageUrl,
      location: category !== '일반' ? location : undefined,
      date: category !== '일반' && date ? new Date(date) : undefined
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
    const { category } = req.query;
    
    let posts;
    
    if (category) {
      // Validate category if provided
      if (!VALID_CATEGORIES.includes(category as PostCategory)) {
        res.status(400).json({
          error: 'Invalid category',
          validCategories: VALID_CATEGORIES
        });
        return;
      }
      posts = await PostModel.findByCategory(category as PostCategory);
    } else {
      posts = await PostModel.findAll();
    }

    res.json({
      success: true,
      data: posts,
      filter: category ? { category } : null
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

// Helper endpoints for convenience
export const getMeetups = async (req: Request, res: Response): Promise<void> => {
  try {
    const meetups = await PostModel.findMeetups();
    res.json({
      success: true,
      data: meetups
    });
  } catch (error) {
    console.error('Error fetching meetups:', error);
    res.status(500).json({
      error: 'Failed to fetch meetups',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const getGeneralPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    const generalPosts = await PostModel.findGeneralPosts();
    res.json({
      success: true,
      data: generalPosts
    });
  } catch (error) {
    console.error('Error fetching general posts:', error);
    res.status(500).json({
      error: 'Failed to fetch general posts',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};