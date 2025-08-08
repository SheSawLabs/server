import { Request, Response } from 'express';
import { PostModel, PostCategory } from '../models/post';
import { ParticipantModel } from '../models/participant';

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

// Meetup participation functions
export const joinMeetup = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const { participant_name } = req.body;
    
    // Validation
    if (!participant_name || participant_name.trim().length === 0) {
      res.status(400).json({
        error: 'Missing required field: participant_name'
      });
      return;
    }

    // Check if post exists and is a meetup
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    if (post.category === '일반') {
      res.status(400).json({
        error: 'Cannot join general posts. Only meetups can be joined.',
        category: post.category
      });
      return;
    }

    // Check if already joined
    const isAlreadyJoined = await ParticipantModel.isParticipant(id, participant_name.trim());
    if (isAlreadyJoined) {
      res.status(409).json({
        error: 'Already joined this meetup',
        participant_name: participant_name.trim()
      });
      return;
    }

    // Join the meetup
    const participant = await ParticipantModel.join({
      post_id: id,
      participant_name: participant_name.trim()
    });

    // Get updated participant count
    const participantCount = await ParticipantModel.getParticipantCount(id);

    res.status(201).json({
      success: true,
      message: 'Successfully joined the meetup',
      data: {
        participant,
        total_participants: participantCount
      }
    });
  } catch (error) {
    console.error('Error joining meetup:', error);
    res.status(500).json({
      error: 'Failed to join meetup',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const leaveMeetup = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const { participant_name } = req.body;
    
    // Validation
    if (!participant_name || participant_name.trim().length === 0) {
      res.status(400).json({
        error: 'Missing required field: participant_name'
      });
      return;
    }

    // Check if post exists and is a meetup
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    if (post.category === '일반') {
      res.status(400).json({
        error: 'Cannot leave general posts. Only meetups can be left.',
        category: post.category
      });
      return;
    }

    // Leave the meetup
    const left = await ParticipantModel.leave(id, participant_name.trim());
    
    if (!left) {
      res.status(404).json({
        error: 'Not a participant of this meetup',
        participant_name: participant_name.trim()
      });
      return;
    }

    // Get updated participant count
    const participantCount = await ParticipantModel.getParticipantCount(id);

    res.json({
      success: true,
      message: 'Successfully left the meetup',
      data: {
        participant_name: participant_name.trim(),
        total_participants: participantCount
      }
    });
  } catch (error) {
    console.error('Error leaving meetup:', error);
    res.status(500).json({
      error: 'Failed to leave meetup',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const getParticipants = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    if (post.category === '일반') {
      res.status(400).json({
        error: 'General posts do not have participants',
        category: post.category
      });
      return;
    }

    // Get participants
    const participants = await ParticipantModel.getByPostId(id);

    res.json({
      success: true,
      data: {
        meetup: {
          id: post.id,
          title: post.title,
          category: post.category,
          location: post.location,
          date: post.date
        },
        participants: participants,
        total_participants: participants.length
      }
    });
  } catch (error) {
    console.error('Error fetching participants:', error);
    res.status(500).json({
      error: 'Failed to fetch participants',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};