import { Request, Response } from 'express';
import { PostModel, PostCategory } from '../models/post';
import { ParticipantModel } from '../models/participant';

const VALID_CATEGORIES: PostCategory[] = ['수리', '소분', '취미', '기타', '일반'];

export const createPost = async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, content, category, location, date, min_participants, max_participants } = req.body;
    const userId = req.user?.user_id;
    
    // Basic validation
    if (!title || !content || !category) {
      res.status(400).json({
        error: 'Missing required fields',
        required: ['title', 'content', 'category']
      });
      return;
    }
    
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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

    // Meetup validation (모임 카테고리는 location, date, 인원 수 필수)
    if (category !== '일반' && (!location || !date || !min_participants || !max_participants)) {
      res.status(400).json({
        error: 'Meetup posts require location, date, and participant limits',
        required: ['location', 'date', 'min_participants', 'max_participants'],
        message: `Category '${category}' requires location, date, and participant limit fields`
      });
      return;
    }

    // Participant limits validation for meetups
    if (category !== '일반') {
      if (min_participants <= 0 || max_participants <= 0 || min_participants > max_participants) {
        res.status(400).json({
          error: 'Invalid participant limits',
          message: 'min_participants and max_participants must be positive, and min_participants <= max_participants'
        });
        return;
      }
    }

    // Handle image URL if file was uploaded
    const imageUrl = req.file ? `/uploads/${req.file.filename}` : undefined;

    const postData = {
      title,
      content,
      category,
      author_id: parseInt(userId),
      image_url: imageUrl,
      location: category !== '일반' ? location : undefined,
      date: category !== '일반' && date ? new Date(date) : undefined,
      min_participants: category !== '일반' ? min_participants : undefined,
      max_participants: category !== '일반' ? max_participants : undefined
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
    const userId = req.user?.user_id;
    
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
      posts = await PostModel.findAll(category as PostCategory, userId);
    } else {
      posts = await PostModel.findAll(undefined, userId);
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
    // 조회수 증가하면서 게시글 가져오기
    const post = await PostModel.findById(id, true);
    
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
    const userId = req.user?.user_id;
    
    // Validation
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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
    const isAlreadyJoined = await ParticipantModel.isParticipant(id, userId);
    if (isAlreadyJoined) {
      res.status(409).json({
        error: 'Already joined this meetup',
        user_id: userId
      });
      return;
    }

    // Check if meetup is full
    const meetupWithParticipants = await PostModel.findMeetupWithParticipants(id);
    if (meetupWithParticipants && meetupWithParticipants.max_participants && 
        meetupWithParticipants.current_participants >= meetupWithParticipants.max_participants) {
      res.status(400).json({
        error: 'Meetup is full',
        current_participants: meetupWithParticipants.current_participants,
        max_participants: meetupWithParticipants.max_participants
      });
      return;
    }

    // Join the meetup
    const participant = await ParticipantModel.join({
      post_id: id,
      user_id: parseInt(userId)
    });

    // Update meetup status based on new participant count
    await PostModel.updateMeetupStatus(id);

    // Get updated participant count and meetup status
    const updatedMeetup = await PostModel.findMeetupWithParticipants(id);

    res.status(201).json({
      success: true,
      message: 'Successfully joined the meetup',
      data: {
        participant,
        meetup_status: updatedMeetup?.status,
        current_participants: updatedMeetup?.current_participants,
        max_participants: updatedMeetup?.max_participants
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
    const userId = req.user?.user_id;
    
    // Validation
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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

    // Check if meetup is active or full - prohibit leaving
    if (post.status === 'active' || post.status === 'full') {
      res.status(400).json({
        error: 'Cannot leave active or full meetups',
        status: post.status,
        message: 'Participants cannot leave meetups that are already active or full'
      });
      return;
    }

    // Leave the meetup
    const left = await ParticipantModel.leave(id, userId);
    
    if (!left) {
      res.status(404).json({
        error: 'Not a participant of this meetup',
        user_id: userId
      });
      return;
    }

    // Update meetup status based on new participant count
    await PostModel.updateMeetupStatus(id);

    // Get updated participant count and meetup status
    const updatedMeetup = await PostModel.findMeetupWithParticipants(id);

    res.json({
      success: true,
      message: 'Successfully left the meetup',
      data: {
        user_id: userId,
        meetup_status: updatedMeetup?.status,
        current_participants: updatedMeetup?.current_participants,
        max_participants: updatedMeetup?.max_participants
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
    const userId = req.user?.user_id;
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    if (post.category === '일반') {
      // For general posts, everyone can view comments
      res.json({
        success: true,
        data: {
          isParticipant: true,
          isAuthor: userId ? post.author_id === parseInt(userId) : false,
          participants: [],
          total_participants: 0
        }
      });
      return;
    }

    // Get participants
    const participants = await ParticipantModel.getByPostId(id);
    
    // Check if current user is author or participant
    const isAuthor = userId ? post.author_id === parseInt(userId) : false;
    const isParticipant = userId ? await ParticipantModel.isParticipant(id, userId) : false;

    res.json({
      success: true,
      data: {
        isParticipant,
        isAuthor,
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

export const getPostSettlement = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        success: false,
        message: 'Post not found'
      });
      return;
    }

    // Import SettlementModel dynamically to avoid circular dependency
    const { SettlementModel } = await import('../models/settlement');
    
    // Get settlement for this post
    const settlement = await SettlementModel.getSettlementByPostId(id);
    
    if (!settlement) {
      res.status(404).json({
        success: false,
        message: '이 게시글에 대한 정산 요청이 없습니다.'
      });
      return;
    }

    res.json({
      success: true,
      data: settlement
    });
  } catch (error) {
    console.error('Error fetching post settlement:', error);
    res.status(500).json({
      success: false,
      message: '정산 정보 조회에 실패했습니다.'
    });
  }
};