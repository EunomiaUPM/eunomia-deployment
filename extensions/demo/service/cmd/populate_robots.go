package main

import (
	"context"
	"eunomia-demo-factory/internal/config"
	"eunomia-demo-factory/internal/database"
	"eunomia-demo-factory/internal/domain"
	"eunomia-demo-factory/internal/repo"

	"github.com/go-faker/faker/v4"
)

func PopulateDB(config *config.Config) error {
	db, err := database.ConnectDB(config)
	if err != nil {
		panic("failed to connect database")
	}
	_ = db
	robotRepository := repo.RobotRepository{
		DB: db,
	}
	robotMeasureRepository := repo.RobotMeasureRepository{
		DB: db,
	}

	// The seed job runs on every `up`: only fill an empty database.
	existing, err := robotRepository.GetAllRobots(context.Background())
	if err != nil {
		return err
	}
	if len(existing) > 0 {
		return nil
	}

	// Create some robots and measures
	// robot 1
	createRobotAndMeasures(&robotRepository, &robotMeasureRepository)
	// robot 2
	createRobotAndMeasures(&robotRepository, &robotMeasureRepository)
	// robot 3
	createRobotAndMeasures(&robotRepository, &robotMeasureRepository)
	// robot 4
	createRobotAndMeasures(&robotRepository, &robotMeasureRepository)
	// robot 5
	createRobotAndMeasures(&robotRepository, &robotMeasureRepository)

	return nil
}

func createRobotAndMeasures(robotRepo *repo.RobotRepository, measureRepo *repo.RobotMeasureRepository) error {
	var robotRequest domain.RobotCreateRequest
	faker.FakeData(&robotRequest)
	robot, _ := robotRepo.CreateRobot(context.Background(), &robotRequest)

	var measureRequest domain.RobotMeasureCreateRequest
	faker.FakeData(&measureRequest)
	measureRequest.RobotID = robot.ID
	measureRepo.CreateRobotMeasure(context.Background(), &measureRequest)

	faker.FakeData(&measureRequest)
	measureRequest.RobotID = robot.ID
	measureRepo.CreateRobotMeasure(context.Background(), &measureRequest)

	faker.FakeData(&measureRequest)
	measureRequest.RobotID = robot.ID
	measureRepo.CreateRobotMeasure(context.Background(), &measureRequest)

	faker.FakeData(&measureRequest)
	measureRequest.RobotID = robot.ID
	measureRepo.CreateRobotMeasure(context.Background(), &measureRequest)

	return nil
}
