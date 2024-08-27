package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// DetectActiveInterface detects the currently active network interface
func DetectActiveInterface() (string, error) {
	interfaces, err := net.Interfaces()
	if err != nil {
		return "", err
	}

	for _, iface := range interfaces {
		if (iface.Flags&net.FlagUp) != 0 && (iface.Flags&net.FlagLoopback) == 0 {
			addrs, err := iface.Addrs()
			if err != nil {
				return "", err
			}
			for _, addr := range addrs {
				if strings.Contains(addr.String(), ".") || strings.Contains(addr.String(), ":") {
					return iface.Name, nil
				}
			}
		}
	}

	return "", fmt.Errorf("no active network interface found")
}

// ReadBytes reads the bytes from /sys/class/net/<interface>/statistics/<rx|tx>_bytes
func ReadBytes(filePath string) (int64, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return 0, err
	}
	bytes, err := strconv.ParseInt(strings.TrimSpace(string(data)), 10, 64)
	if err != nil {
		return 0, err
	}
	return bytes, nil
}

// GetNetworkSpeed calculates the download and upload speeds in bytes per second
func GetNetworkSpeed(interfaceName string, interval time.Duration) (int64, int64, error) {
	rxPath := fmt.Sprintf("/sys/class/net/%s/statistics/rx_bytes", interfaceName)
	txPath := fmt.Sprintf("/sys/class/net/%s/statistics/tx_bytes", interfaceName)

	rxBytesStart, err := ReadBytes(rxPath)
	if err != nil {
		return 0, 0, err
	}
	txBytesStart, err := ReadBytes(txPath)
	if err != nil {
		return 0, 0, err
	}

	time.Sleep(interval)

	rxBytesEnd, err := ReadBytes(rxPath)
	if err != nil {
		return 0, 0, err
	}
	txBytesEnd, err := ReadBytes(txPath)
	if err != nil {
		return 0, 0, err
	}

	rxSpeed := (rxBytesEnd - rxBytesStart) / int64(interval.Seconds())
	txSpeed := (txBytesEnd - txBytesStart) / int64(interval.Seconds())

	return rxSpeed, txSpeed, nil
}

// ConvertBytes converts the speed to the preferred unit, automatically downgrading the unit if necessary
func ConvertBytes(speed int64) (float64, string) {
	const (
		KB = 1024
		MB = 1024 * KB
		GB = 1024 * MB
	)

	if speed >= GB {
		return float64(speed) / GB, "GB/s"
	} else if speed >= MB {
		return float64(speed) / MB, "MB/s"
	} else if speed >= KB {
		return float64(speed) / KB, "KB/s"
	}
	return float64(speed), "B/s"
}

func main() {
	// Define and parse flags
	interval := flag.Int("interval", 1, "Interval in seconds to measure network speed")
	continuous := flag.Bool("c", false, "Run continuously, printing the speed at each interval")
	showDownload := flag.Bool("d", true, "Show download speed")
	showUpload := flag.Bool("u", false, "Show upload speed")
	showAll := flag.Bool("a", false, "Show both download and upload speeds")
	flag.Parse()

	// Adjust flags if -a is provided
	if *showAll {
		*showDownload = true
		*showUpload = true
	}

	// Detect the active network interface
	interfaceName, err := DetectActiveInterface()
	if err != nil {
		log.Fatalf("Failed to detect active network interface: %v", err)
	}

	// Set up signal handling for graceful shutdown
	sigs := make(chan os.Signal, 1)
	done := make(chan bool, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigs
		fmt.Println()
		fmt.Printf("Received signal: %s, shutting down...\n", sig)
		done <- true
	}()

	printSpeed := func() {
		rxSpeed, txSpeed, err := GetNetworkSpeed(interfaceName, time.Duration(*interval)*time.Second)
		if err != nil {
			log.Printf("Failed to get network speed: %v", err)
			return
		}

		if *showDownload {
			downloadSpeed, downloadUnit := ConvertBytes(rxSpeed)
			fmt.Printf("%.2f %s\n", downloadSpeed, downloadUnit)
		}

		if *showUpload {
			uploadSpeed, uploadUnit := ConvertBytes(txSpeed)
			fmt.Printf("%.2f %s\n", uploadSpeed, uploadUnit)
		}
	}

	if *continuous {
		fmt.Printf("Monitoring network speed on interface: %s\n", interfaceName)
		for {
			select {
			case <-done:
				return
			default:
				printSpeed()
			}
		}
	} else {
		printSpeed()
	}
}
