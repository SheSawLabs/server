import { Request, Response } from 'express';
import { CommentModel } from '../models/comment';
import { PostModel } from '../models/post';
import { ParticipantModel } from '../models/participant';
import { LikeModel } from '../models/like';
import { CommentLikeModel } from '../models/commentLike';

// Create comment
export const createComment = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params; // post_id
    const { content, parent_comment_id } = req.body;
    const userId = req.user?.user_id;
    
    // Validation
    if (!content || content.trim().length === 0) {
      res.status(400).json({
        error: 'Missing required fields',
        required: ['content']
      });
      return;
    }
    
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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

    // For meetups (non-general posts), check if user is the author or a participant
    if (post.category !== '일반') {
      const isAuthor = post.author_id === parseInt(userId);
      const isParticipant = await ParticipantModel.isParticipant(id, userId);
      
      if (!isAuthor && !isParticipant) {
        res.status(403).json({
          error: 'Only meetup author or participants can comment',
          message: 'You must be the meetup author or join this meetup to comment'
        });
        return;
      }
    }

    // If replying to a comment, validate parent comment exists
    if (parent_comment_id) {
      const parentComment = await CommentModel.findById(parent_comment_id);
      if (!parentComment) {
        res.status(404).json({
          error: 'Parent comment not found'
        });
        return;
      }

      // Ensure parent comment belongs to this post
      if (parentComment.post_id !== id) {
        res.status(400).json({
          error: 'Parent comment does not belong to this post'
        });
        return;
      }
    }

    // Create comment
    const comment = await CommentModel.create({
      post_id: id,
      parent_comment_id: parent_comment_id || undefined,
      author_id: parseInt(userId),
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
    const userId = req.user?.user_id; // From JWT token (optional auth)
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // For meetups (non-general posts), check if user is the author or a participant
    if (post.category !== '일반') {
      if (!userId) {
        res.status(401).json({
          error: 'Authentication required for meetup comments',
          message: 'You must be logged in to view meetup comments'
        });
        return;
      }

      const isAuthor = post.author_id === parseInt(userId);
      const isParticipant = await ParticipantModel.isParticipant(id, userId);
      
      if (!isAuthor && !isParticipant) {
        res.status(403).json({
          error: 'Only meetup author or participants can view comments',
          message: 'You must be the meetup author or join this meetup to view comments'
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
    const userId = req.user?.user_id;
    
    // Validation
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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
    const deleted = await CommentModel.deleteById(commentId, parseInt(userId));
    
    if (!deleted) {
      res.status(403).json({
        error: 'Only the comment author can delete this comment'
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
    const userId = req.user?.user_id;
    
    // Validation
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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
      user_id: parseInt(userId)
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
    const userId = req.user?.user_id; // From JWT token (optional auth)
    
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
    
    // Check if current user liked (if userId provided)
    let isLiked = false;
    if (userId) {
      isLiked = await LikeModel.isLikedByUser(id, parseInt(userId));
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

// Toggle like on comment
export const toggleCommentLike = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id, commentId } = req.params; // post_id, comment_id
    const userId = req.user?.user_id;
    
    // Validation
    if (!userId) {
      res.status(401).json({
        error: 'User not authenticated'
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

    // Check if comment exists and belongs to this post
    const comment = await CommentModel.findById(commentId);
    if (!comment) {
      res.status(404).json({
        error: 'Comment not found'
      });
      return;
    }

    if (comment.post_id !== id) {
      res.status(400).json({
        error: 'Comment does not belong to this post'
      });
      return;
    }

    // Toggle comment like
    const result = await CommentLikeModel.toggle({
      comment_id: commentId,
      user_id: parseInt(userId)
    });

    res.json({
      success: true,
      message: result.liked ? 'Comment liked' : 'Comment unliked',
      data: {
        comment_id: commentId,
        liked: result.liked,
        like_count: result.likeCount
      }
    });
  } catch (error) {
    console.error('Error toggling comment like:', error);
    res.status(500).json({
      error: 'Failed to toggle comment like',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

// Get like count for comment
export const getCommentLikes = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id, commentId } = req.params; // post_id, comment_id
    const userId = req.user?.user_id; // From JWT token (optional auth)
    
    // Check if post exists
    const post = await PostModel.findById(id);
    if (!post) {
      res.status(404).json({
        error: 'Post not found'
      });
      return;
    }

    // Check if comment exists and belongs to this post
    const comment = await CommentModel.findById(commentId);
    if (!comment) {
      res.status(404).json({
        error: 'Comment not found'
      });
      return;
    }

    if (comment.post_id !== id) {
      res.status(400).json({
        error: 'Comment does not belong to this post'
      });
      return;
    }

    // Get like count
    const likeCount = await CommentLikeModel.getCountByCommentId(commentId);
    
    // Check if current user liked (if userId provided)
    let isLiked = false;
    if (userId) {
      isLiked = await CommentLikeModel.isLikedByUser(commentId, parseInt(userId));
    }

    res.json({
      success: true,
      data: {
        comment_id: commentId,
        like_count: likeCount,
        is_liked: isLiked
      }
    });
  } catch (error) {
    console.error('Error fetching comment likes:', error);
    res.status(500).json({
      error: 'Failed to fetch comment likes',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};