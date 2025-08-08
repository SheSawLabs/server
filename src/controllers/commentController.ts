import { Request, Response } from 'express';
import { CommentModel } from '../models/comment';
import { PostModel } from '../models/post';
import { ParticipantModel } from '../models/participant';
import { LikeModel } from '../models/like';

// Create comment
export const createComment = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params; // post_id
    const { author_name, content } = req.body;
    
    // Validation
    if (!author_name || !content || author_name.trim().length === 0 || content.trim().length === 0) {
      res.status(400).json({
        error: 'Missing required fields',
        required: ['author_name', 'content']
      });
      return;
    }

    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // For meetups (non-general posts), check if user is a participant
    if (post.category !== '일반') {
      const isParticipant = await ParticipantModel.isParticipant(id, author_name.trim());
      if (!isParticipant) {
        res.status(403).json({
          error: 'Only meetup participants can comment',
          message: 'You must join this meetup to comment'
        });
        return;
      }
    }

    // Create comment
    const comment = await CommentModel.create({
      post_id: id,
      author_name: author_name.trim(),
      content: content.trim()
    });

    res.status(201).json({
      success: true,
      message: 'Comment created successfully',
      data: comment
    });
  } catch (error) {
    console.error('Error creating comment:', error);
    res.status(500).json({
      error: 'Failed to create comment',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

// Get comments for a post
export const getComments = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params; // post_id
    const { user_name } = req.query; // For meetup access control
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // For meetups (non-general posts), check if user is a participant
    if (post.category !== '일반') {
      if (!user_name || typeof user_name !== 'string') {
        res.status(400).json({
          error: 'user_name query parameter is required for meetup comments',
          message: 'Provide ?user_name=your_name to view meetup comments'
        });
        return;
      }

      const isParticipant = await ParticipantModel.isParticipant(id, user_name.trim());
      if (!isParticipant) {
        res.status(403).json({
          error: 'Only meetup participants can view comments',
          message: 'You must join this meetup to view comments'
        });
        return;
      }
    }

    // Get comments
    const comments = await CommentModel.getByPostId(id);
    const commentCount = comments.length;

    res.json({
      success: true,
      data: {
        post: {
          id: post.id,
          title: post.title,
          category: post.category
        },
        comments,
        comment_count: commentCount
      }
    });
  } catch (error) {
    console.error('Error fetching comments:', error);
    res.status(500).json({
      error: 'Failed to fetch comments',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

// Delete comment
export const deleteComment = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id, commentId } = req.params; // post_id, comment_id
    const { author_name } = req.body;
    
    // Validation
    if (!author_name || author_name.trim().length === 0) {
      res.status(400).json({
        error: 'Missing required field: author_name'
      });
      return;
    }

    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // Check if comment exists
    const comment = await CommentModel.findById(commentId);
    if (!comment) {
      res.status(404).json({
        error: 'Comment not found'
      });
      return;
    }

    // Verify comment belongs to this post
    if (comment.post_id !== id) {
      res.status(400).json({
        error: 'Comment does not belong to this post'
      });
      return;
    }

    // Delete comment (only author can delete)
    const deleted = await CommentModel.deleteById(commentId, author_name.trim());
    
    if (!deleted) {
      res.status(403).json({
        error: 'Only the comment author can delete this comment',
        author: comment.author_name
      });
      return;
    }

    res.json({
      success: true,
      message: 'Comment deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting comment:', error);
    res.status(500).json({
      error: 'Failed to delete comment',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

// Toggle like on post
export const toggleLike = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params; // post_id
    const { user_name } = req.body;
    
    // Validation
    if (!user_name || user_name.trim().length === 0) {
      res.status(400).json({
        error: 'Missing required field: user_name'
      });
      return;
    }

    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // Toggle like
    const result = await LikeModel.toggle({
      post_id: id,
      user_name: user_name.trim()
    });

    res.json({
      success: true,
      message: result.liked ? 'Post liked' : 'Post unliked',
      data: {
        liked: result.liked,
        like_count: result.likeCount
      }
    });
  } catch (error) {
    console.error('Error toggling like:', error);
    res.status(500).json({
      error: 'Failed to toggle like',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

// Get like count for post
export const getLikes = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params; // post_id
    const { user_name } = req.query;
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // Get like count
    const likeCount = await LikeModel.getCountByPostId(id);
    
    // Check if current user liked (if user_name provided)
    let isLiked = false;
    if (user_name && typeof user_name === 'string') {
      isLiked = await LikeModel.isLikedByUser(id, user_name.trim());
    }

    res.json({
      success: true,
      data: {
        post_id: id,
        like_count: likeCount,
        is_liked: isLiked
      }
    });
  } catch (error) {
    console.error('Error fetching likes:', error);
    res.status(500).json({
      error: 'Failed to fetch likes',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};