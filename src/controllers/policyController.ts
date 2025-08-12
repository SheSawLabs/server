import { Request, Response } from 'express';
import { PolicyModel } from '../models/policy';

export const getPolicies = async (req: Request, res: Response): Promise<void> => {
  try {
    const { category } = req.query;
    
    let policies;
    
    if (category) {
      policies = await PolicyModel.findByCategory(category as string);
    } else {
      policies = await PolicyModel.findAll();
    }

    res.json({
      success: true,
      data: policies,
      filter: category ? { category } : null
    });
  } catch (error) {
    console.error('Error fetching policies:', error);
    res.status(500).json({
      error: 'Failed to fetch policies',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const getPolicyById = async (req: Request, res: Response): Promise<void> => {
  try {
    const { id } = req.params;
    const policy = await PolicyModel.findById(id);
    
    if (!policy) {
      res.status(404).json({
        error: 'Policy not found'
      });
      return;
    }

    res.json({
      success: true,
      data: policy
    });
  } catch (error) {
    console.error('Error fetching policy:', error);
    res.status(500).json({
      error: 'Failed to fetch policy',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};

export const deleteAllPolicies = async (req: Request, res: Response): Promise<void> => {
  try {
    const deletedCount = await PolicyModel.deleteAll();
    
    res.json({
      success: true,
      message: `Successfully deleted ${deletedCount} policies`,
      deletedCount
    });
  } catch (error) {
    console.error('Error deleting all policies:', error);
    res.status(500).json({
      error: 'Failed to delete all policies',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
};