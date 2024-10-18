package tools

import (
	"archive/zip"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"

	"github.com/pdfcpu/pdfcpu/pkg/api"
)

func GetTotalPages(pdfPath string) (int, error) {
	ctx, err := api.ReadContextFile(pdfPath)
	if err != nil {
		return 0, err
	}
	return ctx.PageCount, nil
}

func convertBatch(pdfPath, outputDir string, startPage, endPage int) error {
	// Construct the command to process a batch of pages
	cmd := exec.Command(
		"pdftoppm", "-jpeg", "-r", "72",
		"-f", fmt.Sprint(startPage), "-l", fmt.Sprint(endPage),
		pdfPath, filepath.Join(outputDir, "page-%03d"),
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	return cmd.Run()
}

// Convert PDF to images using ImageMagick
func pdfToImages(pdfPath, outputDir string) error {
	totalPages, err := GetTotalPages(pdfPath)
	fmt.Println("Total pages:", totalPages)
	if err != nil {
		return err
	}
	batchSize := 5
	batch := os.Getenv("batchSize")
	if batch != "" {
		batchSize, _ = strconv.Atoi(batch)
	}
	for i := 1; i <= totalPages; i += batchSize {
		end := i + batchSize - 1
		if end > totalPages {
			end = totalPages
		}
		fmt.Printf("Processing pages %d to %d...\n", i, end)
		if err := convertBatch(pdfPath, outputDir, i, end); err != nil {
			fmt.Printf("Error processing batch %d-%d: %v\n", i, end, err)
			break
		}
	}

	return nil
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
