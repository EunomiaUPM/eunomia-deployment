package repo

import (
	"context"
	"eunomia-demo-factory/internal/domain"

	"gorm.io/gorm"
)

type RobotRepository struct {
	DB *gorm.DB
}

func (repo *RobotRepository) GetAllRobots(ctx context.Context) ([]domain.RobotModel, error) {
	var robots []domain.RobotModel
	err := repo.DB.WithContext(ctx).Find(&robots).Error
	return robots, err
}

func (repo *RobotRepository) CreateRobot(ctx context.Context, newRobot *domain.RobotCreateRequest) (domain.RobotModel, error) {
	robot := domain.RobotModel{
		Name:      newRobot.Name,
		ModelName: newRobot.ModelName,
		Line:      newRobot.Line,
	}
	err := repo.DB.WithContext(ctx).Create(&robot).Error
	return robot, err
}

func (repo *RobotRepository) GetRobotByID(ctx context.Context, id uint) (domain.RobotModel, error) {
	var robot domain.RobotModel
	err := repo.DB.WithContext(ctx).First(&robot, id).Error
	return robot, err
}

func (repo *RobotRepository) UpdateRobot(ctx context.Context, id uint, updatedRobot *domain.RobotUpdateRequest) (domain.RobotModel, error) {
	return domain.RobotModel{}, nil
}

func (repo *RobotRepository) DeleteRobot(ctx context.Context, id uint) error {
	return nil
}
