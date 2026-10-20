package repo

import (
	"eunomia-demo-factory/internal/domain"

	"gorm.io/gorm"
)

type RobotEventRepository struct {
	DB *gorm.DB
}

func (repo *RobotEventRepository) TableName() string {
	return "robot_events"
}

func (repo *RobotEventRepository) CreateRobotEvent(newEvent *domain.RobotEventCreateRequest) (domain.RobotEvent, error) {
	event := domain.RobotEvent{
		RobotID:      newEvent.RobotID,
		EventName:    newEvent.EventName,
		EventContent: newEvent.EventContent,
	}
	err := repo.DB.Create(&event).Error
	return event, err
}

func (repo *RobotEventRepository) GetAllRobotEvents() ([]domain.RobotEvent, error) {
	var events []domain.RobotEvent
	err := repo.DB.Find(&events).Error
	return events, err
}

func (repo *RobotEventRepository) GetRobotEventByID(id uint) (domain.RobotEvent, error) {
	var event domain.RobotEvent
	err := repo.DB.First(&event, id).Error
	return event, err
}

func (repo *RobotEventRepository) DeleteRobotEvent(id uint) error {
	return repo.DB.Delete(&domain.RobotEvent{}, id).Error
}
