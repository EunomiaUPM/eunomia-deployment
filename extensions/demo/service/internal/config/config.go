package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	DatabaseHost            string
	DatabasePort            string
	DatabaseUser            string
	DatabasePass            string
	DatabaseName            string
	StaticServerPort        string
	StaticServerHost        string
	DynamicStaticServerPort string
	DynamicStaticServerHost string
	KeycloakURL             string
	KeycloakRealm           string
	KeycloakClientID        string
}

func LoadConfig() *Config {
	err := godotenv.Load()
	if err != nil {
		log.Println("No .env file found, using environment variables")
	}

	config := &Config{
		DatabaseHost:            os.Getenv("DATABASE_HOST"),
		DatabasePort:            os.Getenv("DATABASE_PORT"),
		DatabaseUser:            os.Getenv("DATABASE_USER"),
		DatabasePass:            os.Getenv("DATABASE_PASS"),
		DatabaseName:            os.Getenv("DATABASE_NAME"),
		StaticServerPort:        os.Getenv("STATIC_SERVER_PORT"),
		StaticServerHost:        os.Getenv("STATIC_SERVER_HOST"),
		DynamicStaticServerPort: os.Getenv("DYNAMIC_SERVER_PORT"),
		DynamicStaticServerHost: os.Getenv("DYNAMIC_SERVER_HOST"),
		KeycloakURL:             os.Getenv("KEYCLOAK_URL"),
		KeycloakRealm:           os.Getenv("KEYCLOAK_REALM"),
		KeycloakClientID:        os.Getenv("KEYCLOAK_CLIENT_ID"),
	}

	return config
}

func (c *Config) GetConfig() *Config {
	return c
}

func (c *Config) GetDatabaseDSN() string {
	return "host=" + c.DatabaseHost +
		" user=" + c.DatabaseUser +
		" password=" + c.DatabasePass +
		" dbname=" + c.DatabaseName +
		" port=" + c.DatabasePort +
		" sslmode=disable"
}

func (c *Config) GetStaticServerAddress() string {
	return c.StaticServerHost + ":" + c.StaticServerPort
}
func (c *Config) GetDynamicServerAddress() string {
	return c.DynamicStaticServerHost + ":" + c.DynamicStaticServerPort
}
