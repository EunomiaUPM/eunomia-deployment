package main

import (
	"context"
	"eunomia-demo-factory/internal/config"
	"eunomia-demo-factory/internal/controllers/http"
	"eunomia-demo-factory/internal/database"
	"eunomia-demo-factory/internal/domain"
	"eunomia-demo-factory/internal/middleware"
	"eunomia-demo-factory/internal/repo"
	"eunomia-demo-factory/internal/services"
	"sync"

	"github.com/gin-gonic/gin"
)

func BootstrapMetricsCollector(config *config.Config) {
	db, err := database.ConnectDB(config)
	if err != nil {
		panic("failed to connect database")
	}
	_ = db

	// Initialize Metric Simulator Service
	var wg sync.WaitGroup
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	notificationService := services.NewNotificationService(
		&repo.SubscriptionRepository{DB: db},
		10,
	)
	go notificationService.Start(ctx, &wg)
	metricSimulatorService := services.NewMetricSimulatorService(
		&repo.MetricItemRepository{DB: db},
		notificationService,
	)

	// Register some metric items
	metricSimulatorService.RegisterMetricItem(&domain.MetricItemCreateRequest{
		ItemType: domain.MetricKeyRobotEnergyUsage,
	})
	metricSimulatorService.RegisterMetricItem(&domain.MetricItemCreateRequest{
		ItemType: domain.MetricKeyRobotCycleTime,
	})
	metricSimulatorService.RegisterMetricItem(&domain.MetricItemCreateRequest{
		ItemType: domain.MetricKeyRobotTemperature,
	})
	metricSimulatorService.RegisterMetricItem(&domain.MetricItemCreateRequest{
		ItemType: domain.MetricKeyRobotVibration,
	})
	// Start the metric simulator
	go metricSimulatorService.Start(ctx)

	// Initialize Notification Service
	router := gin.Default()

	// Public routes (Documentation)
	router.StaticFile("/openapi.yaml", "./specs/openapi/robots.yaml")
	router.GET("/docs", func(c *gin.Context) {
		c.Header("Content-Type", "text/html")
		c.String(200, `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Demo Factory API Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: "/openapi.yaml",
        dom_id: '#swagger-ui',
      });
    };
  </script>
</body>
</html>`)
	})

	router.Use(middleware.AuthMiddleware(config))
	subscriptionsRouter := http.SubscriptionsRouter{
		SubscriptionService: services.NewSubscriptionService(
			&repo.SubscriptionRepository{DB: db},
		),
	}
	subscriptionsRouter.Create(router)

	router.Run(config.GetDynamicServerAddress()) // listens on
}
