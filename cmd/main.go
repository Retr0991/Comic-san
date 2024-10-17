package main

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"Comic-san/tools"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	bot, err := tgbotapi.NewBotAPI(os.Getenv("API_TOKEN"))
	if err != nil {
		panic(err)
	}

	bot.Debug = true
	log.Printf("Authorized on account %s", bot.Self.UserName)

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)

	updates := bot.GetUpdatesChan(u)

	go receiveUpdates(ctx, updates, bot)

	log.Println("Bot is running. Press enter to stop.")

	bufio.NewReader(os.Stdin).ReadBytes('\n')
	cancel()
}

func receiveUpdates(ctx context.Context, updates tgbotapi.UpdatesChannel, bot *tgbotapi.BotAPI) {
	for {
		select {
		case <-ctx.Done():
			log.Println("Stopping bot.")
			return
		case update := <-updates:
			handleUpdates(update, bot)
		}
	}
}

func handleUpdates(update tgbotapi.Update, bot *tgbotapi.BotAPI) {
	switch {
	// Handle messages
	case update.Message != nil:
		if update.Message.Document != nil && update.Message.Document.MimeType == "application/pdf" {
			// Get the file from Telegram
			fileID := update.Message.Document.FileID
			file, err := bot.GetFile(tgbotapi.FileConfig{FileID: fileID})
			if err != nil {
				log.Println(err)
				return
			}

			// Download the file
			fileName := update.Message.Document.FileName
			_, err = os.Stat("../downloads")
			if os.IsNotExist(err) {
				os.Mkdir("../downloads", 0755)
			}
			saveTo := "../downloads/" + fileName
			err = downloadFile(bot, file.FilePath, saveTo)
			if err != nil {
				log.Println(err)
				return
			} else {
				log.Printf("File %s downloaded successfully.", fileName)
			}

			// Convert the PDF to CBZ
			convertedFile := tools.ConvertToCBZ(saveTo, fileName[:len(fileName)-4])

			// Send the CBZ file to the user

			cbzFile := tgbotapi.NewDocument(update.Message.Chat.ID, tgbotapi.FilePath(convertedFile))

			cbzFile.Caption = "Here is your file!"

            // Send the file to the user
            if _, err := bot.Send(cbzFile); err != nil {
                log.Printf("Error sending document: %v", err)
            }

			// Remove the downloaded and cbz files
			log.Printf("Removing files %s and %s", saveTo, convertedFile)
			os.Remove(saveTo)
			os.Remove(convertedFile)
		}
		break

	// Handle Callback queries
	case update.CallbackQuery != nil:
		break
	}
}

func downloadFile(bot *tgbotapi.BotAPI, filePath, saveTo string) error {
	url := fmt.Sprintf("https://api.telegram.org/file/bot%s/%s", bot.Token, filePath)

	// Create the file locally
	out, err := os.Create(saveTo)
	if err != nil {
		return err
	}
	defer out.Close()

	// Send the HTTP request to download the file
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Copy the file content to the local file
	_, err = io.Copy(out, resp.Body)
	return err
}