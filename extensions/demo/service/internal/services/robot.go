package services

import (
	"context"

	"eunomia-demo-factory/internal/domain"
	"eunomia-demo-factory/internal/repo"
)

type RobotService struct {
	RobotRepository        *repo.RobotRepository
	RobotMeasureRepository *repo.RobotMeasureRepository
}

func (service *RobotService) CreateRobot(ctx context.Context, newRobot *domain.RobotCreateRequest) (domain.Robot, error) {
	robot, err := service.RobotRepository.CreateRobot(ctx, newRobot)
	measures := []domain.RobotMeasure{}
	robotWithMeasures := domain.Robot{
		Name:      robot.Name,
		ModelName: robot.ModelName,
		Line:      robot.Line,
		Measures:  measures,
	}
	return robotWithMeasures, err
}

func (service *RobotService) GetAllRobots(ctx context.Context) ([]domain.Robot, error) {
	robots, err := service.RobotRepository.GetAllRobots(ctx)
	if err != nil {
		return nil, err
	}
	var robotsWithMeasures []domain.Robot
	for _, robot := range robots {
		measures, err := service.RobotMeasureRepository.GetRobotMeasuresByRobotID(ctx, robot.ID)
		if err != nil {
			return nil, err
		}
		robotWithMeasures := domain.Robot{
			Name:      robot.Name,
			ModelName: robot.ModelName,
			Line:      robot.Line,
			Measures:  measures,
		}
		robotsWithMeasures = append(robotsWithMeasures, robotWithMeasures)
	}
	return robotsWithMeasures, nil
}

func (service *RobotService) GetRobotByID(ctx context.Context, id uint) (domain.Robot, error) {
	robot, err := service.RobotRepository.GetRobotByID(ctx, id)
	if err != nil {
		return domain.Robot{}, err
	}
	measures, err := service.RobotMeasureRepository.GetRobotMeasuresByRobotID(ctx, robot.ID)
	if err != nil {
		return domain.Robot{}, err
	}
	robotWithMeasures := domain.Robot{
		Name:      robot.Name,
		ModelName: robot.ModelName,
		Line:      robot.Line,
		Measures:  measures,
	}
	return robotWithMeasures, nil
}

func (service *RobotService) CreateRobotMeasure(ctx context.Context, newMeasure *domain.RobotMeasureCreateRequest) (domain.RobotMeasure, error) {
	return service.RobotMeasureRepository.CreateRobotMeasure(ctx, newMeasure)
}

func (service *RobotService) GetAllRobotMeasures(ctx context.Context) ([]domain.RobotMeasure, error) {
	return service.RobotMeasureRepository.GetAllRobotMeasures(ctx)
}

func (service *RobotService) GetRobotMeasureByID(ctx context.Context, id uint) (domain.RobotMeasure, error) {
	return service.RobotMeasureRepository.GetRobotMeasureByID(ctx, id)
}

func (service *RobotService) GetRobotMeasuresByRobotID(ctx context.Context, robotID uint) ([]domain.RobotMeasure, error) {
	return service.RobotMeasureRepository.GetRobotMeasuresByRobotID(ctx, robotID)
}

func (service *RobotService) DeleteRobotMeasure(ctx context.Context, id uint) error {
	return service.RobotMeasureRepository.DeleteRobotMeasure(ctx, id)
}
