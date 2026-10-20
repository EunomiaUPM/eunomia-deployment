package main

import (
	"eunomia-demo-factory/internal/config"
	"eunomia-demo-factory/internal/controllers/http"
	"eunomia-demo-factory/internal/middleware"
	"eunomia-demo-factory/internal/repo"
	"eunomia-demo-factory/internal/services"

	"eunomia-demo-factory/internal/database"

	"github.com/gin-gonic/gin"
)

func BootstrapHTTPServer(config *config.Config) {
	db, err := database.ConnectDB(config)
	if err != nil {
		panic("failed to connect database")
	}
	_ = db

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

	// Apply Auth Middleware
	router.Use(middleware.AuthMiddleware(config))

	robotRouter := http.RobotRouter{
		RobotService: services.RobotService{
			RobotRepository:        &repo.RobotRepository{DB: db},
			RobotMeasureRepository: &repo.RobotMeasureRepository{DB: db},
		},
	}
	robotRouter.Create(router)

	router.Run(config.GetStaticServerAddress()) // listens on 0.0.0.0:8080 by default
}
