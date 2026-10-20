package main

import (
	"eunomia-demo-factory/internal/config"
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "eunomia-demo-factory",
	Short: "EUNOMIA demo factory API server",
	Long:  `A fake API server for a factory: robots and their yearly measures (pull), and the events the robots emit (push).`,
}

var serve = &cobra.Command{
	Use:   "serve",
	Short: "Start the HTTP server",
	Run: func(cmd *cobra.Command, args []string) {
		config := config.LoadConfig()
		BootstrapHTTPServer(config)
	},
}

var populateDB = &cobra.Command{
	Use:   "fake",
	Short: "Populate the database with sample data",
	Run: func(cmd *cobra.Command, args []string) {
		config := config.LoadConfig()
		err := PopulateDB(config)
		if err != nil {
			fmt.Println("Error populating database:", err)
			os.Exit(1)
		}
		fmt.Println("Database populated successfully.")
	},
}

var metrics = &cobra.Command{
	Use:   "metrics",
	Short: "Start the Metrics collector",
	Run: func(cmd *cobra.Command, args []string) {
		config := config.LoadConfig()
		BootstrapMetricsCollector(config)
	},
}

func init() {
	rootCmd.AddCommand(serve)
	rootCmd.AddCommand(populateDB)
	rootCmd.AddCommand(metrics)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
