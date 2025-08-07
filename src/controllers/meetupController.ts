import { Request, Response } from 'express';
import { MeetupModel } from '../models/meetup';

export const createMeetup = async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, content, location, date } = req.body;
    
    // Validation
    if (!title || !content || !location || !date) {
      res.status(400).json({
        error: 'Missing required fields',
        required: ['title', 'content', 'location', 'date']
      });
      return;
    }

    // Handle image URL if file was uploaded
    const imageUrl = req.file ? `/uploads/${req.file.filename}` : undefined;

    const meetupData = {
      title,
      content,
      image_url: imageUrl,
      location,
      date: new Date(date)
    };

    const newMeetup = await MeetupModel.create(meetupData);

    res.status(201).json({
      success: true,
      data: newMeetup
    });
  } catch (error) {
    console.error('Error creating meetup:', error);
    res.status(500).json({
      error: 'Failed to create meetup',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const getMeetups = async (req: Request, res: Response) => {
  try {
    const meetups = await MeetupModel.findAll();
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

export const getMeetupById = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const meetup = await MeetupModel.findById(id);
    
    if (!meetup) {
      res.status(404).json({
        error: 'Meetup not found'
      });
      return;
    }

    res.json({
      success: true,
      data: meetup
    });
  } catch (error) {
    console.error('Error fetching meetup:', error);
    res.status(500).json({
      error: 'Failed to fetch meetup',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};