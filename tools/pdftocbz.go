package tools

import (
	"archive/zip"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
)

// Convert PDF to images using ImageMagick
func pdfToImages(pdfPath, outputDir string) error {
	cmd := exec.Command("pdftoppm", "-jpeg -r 72", pdfPath, filepath.Join(outputDir, "page-%03d"))
	return cmd.Run()
}

// Create a CBZ archive from images
func createCBZ(imagesDir, cbzPath string) error {
	cbzFile, err := os.Create(cbzPath)
	if err != nil {
		return err
	}
	defer cbzFile.Close()

	zipWriter := zip.NewWriter(cbzFile)
	defer zipWriter.Close()

	err = filepath.Walk(imagesDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}

		file, err := os.Open(path)
		if err != nil {
			return err
		}
		defer file.Close()

		// Create a new zip entry for each image
		zipEntry, err := zipWriter.Create(info.Name())
		if err != nil {
			return err
		}

		_, err = io.Copy(zipEntry, file)
		return err
	})

	return err
}

func ConvertToCBZ(pdfPath, fileName string) string {
	imagesDir := "images"
	cbzPath := fmt.Sprintf("%s.cbz", fileName)

	// Step 1: Create a directory to store the extracted images
	if err := os.MkdirAll(imagesDir, 0755); err != nil {
		log.Fatalf("Failed to create images directory: %v", err)
	}

	// Step 2: Convert PDF to images
	log.Println("Extracting PDF pages as images...")
	if err := pdfToImages(pdfPath, imagesDir); err != nil {
		log.Fatalf("Failed to convert PDF to images: %v", err)
	}

	// Step 3: Create CBZ from images
	log.Println("Creating CBZ archive...")
	if err := createCBZ(imagesDir, cbzPath); err != nil {
		log.Fatalf("Failed to create CBZ file: %v", err)
	}

	// Step 4: Cleanup - remove the images directory
	log.Println("Cleaning up...")
	if err := os.RemoveAll(imagesDir); err != nil {
		log.Fatalf("Failed to remove images directory: %v", err)
	}

	log.Println("Conversion completed! Output:", cbzPath)

	return cbzPath
}
