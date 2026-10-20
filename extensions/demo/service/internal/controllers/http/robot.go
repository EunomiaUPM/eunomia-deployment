package http

import (
	"eunomia-demo-factory/internal/domain"
	"eunomia-demo-factory/internal/services"
	"strconv"

	"github.com/gin-gonic/gin"
)

type RobotRouter struct {
	RobotService services.RobotService
}

func (r *RobotRouter) Create(router *gin.Engine) {
	robotGroup := router.Group("/robots")
	robotGroup.GET("/", r.getAllRobots)
	robotGroup.POST("/", r.createRobot)
	robotGroup.GET("/:id", r.getRobotById)
	robotGroup.GET("/:id/measures", r.getMeasuresByRobotId)
	measuresGroup := router.Group("/measures")
	measuresGroup.POST("/", r.createMeasure)
	measuresGroup.GET("/:id", r.getMeasureById)
}

func (r *RobotRouter) getAllRobots(c *gin.Context) {
	robots, err := r.RobotService.GetAllRobots(c.Request.Context())
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(200, robots)
}

func (r *RobotRouter) createRobot(c *gin.Context) {
	var newRobot domain.RobotCreateRequest
	if err := c.ShouldBindJSON(&newRobot); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	robot, err := r.RobotService.CreateRobot(c.Request.Context(), &newRobot)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(201, robot)
}

func (r *RobotRouter) getRobotById(c *gin.Context) {
	id := c.Param("id")
	uid, err := strconv.ParseUint(id, 10, 32)
	if err != nil {
		c.JSON(400, gin.H{"error": "Invalid robot ID"})
		return
	}
	robot, err := r.RobotService.GetRobotByID(c.Request.Context(), uint(uid))
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(200, robot)
}

func (r *RobotRouter) createMeasure(c *gin.Context) {
	var newMeasure domain.RobotMeasureCreateRequest
	if err := c.ShouldBindJSON(&newMeasure); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	measure, err := r.RobotService.CreateRobotMeasure(c.Request.Context(), &newMeasure)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(201, measure)
}

func (r *RobotRouter) getMeasuresByRobotId(c *gin.Context) {
	id := c.Param("id")
	uid, err := strconv.ParseUint(id, 10, 32)
	if err != nil {
		c.JSON(400, gin.H{"error": "Invalid robot ID"})
		return
	}
	measures, err := r.RobotService.GetRobotMeasuresByRobotID(c.Request.Context(), uint(uid))
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(200, measures)
}

func (r *RobotRouter) getMeasureById(c *gin.Context) {
	id := c.Param("id")
	uid, err := strconv.ParseUint(id, 10, 32)
	if err != nil {
		c.JSON(400, gin.H{"error": "Invalid measure ID"})
		return
	}
	measure, err := r.RobotService.GetRobotMeasureByID(c.Request.Context(), uint(uid))
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(200, measure)
}
