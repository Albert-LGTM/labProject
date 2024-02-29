// Package plugindemo a demo plugin.
package ACLAuthenticate

import (
	"bytes"
	"context"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
	"encoding/json"
	"text/template"
)

// Config the plugin configuration.
type Config struct {
	Groups    string `json:"groups,omitempty"`
	Tags     string `json:"tags,omitempty"`
}

// CreateConfig creates the default plugin configuration.
func CreateConfig() *Config {
	return &Config{}
}

// Demo a Demo plugin.
type Demo struct {
	next     http.Handler
	groups	 string
	tags	 string
	name     string
	template *template.Template
}
// New created a new Demo plugin.
func New(ctx context.Context, next http.Handler, config *Config, name string) (http.Handler, error) {
	if config.Tags == "" || config.Groups == "" {
		return nil, fmt.Errorf("You need to add groups and tags label.. Make sure you use tags/groups and not tag/group")
	 }
	return &Demo{
		groups:	 config.Groups,
		tags:	 config.Tags,
		next:     next,
		name:     name,
		template: template.New("demo").Delims("[[", "]]"),
	}, nil
}

func (a *Demo) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
	requestedWebsite := req.Host
	requesterIP := strings.Split(req.RemoteAddr, ":")[0]
	//requesterIP := req.Header.Get("x-real-ip")
	fmt.Fprintln(rw, "Requested Website: ",  requestedWebsite)
	fmt.Fprintln(rw, "Requested Groups: ", a.groups)
	fmt.Fprintln(rw, "Requseted Tags: ", a.tags)
	fmt.Fprintln(rw, "Requested IP: ", requesterIP)


	// Construct the API URL with the requester's IP
	apiURL := fmt.Sprintf("http://fedora:4444/api/authorization/%s/%s/%s", a.tags,  a.groups, requesterIP)
        apiResp, err := http.Get(apiURL)
	fmt.Fprintln(rw, "Requested URL", apiURL)
        if err != nil {
                http.Error(rw, err.Error(), http.StatusInternalServerError)
                return
        }

        defer apiResp.Body.Close()

        // Read the response body
        responseBody, err := ioutil.ReadAll(apiResp.Body)
        if err != nil {
                http.Error(rw, err.Error(), http.StatusInternalServerError)
                return
        }

        // Parse the JSON response
        var jsonResponse map[string]interface{}
        if err := json.Unmarshal(responseBody, &jsonResponse); err != nil {
                http.Error(rw, err.Error(), http.StatusInternalServerError)
                return
        }

        // Check the value of the "authenticated?" field
        if present, ok := jsonResponse["authenticated?"].(bool); ok && present {
                fmt.Fprintln(rw, "URL Returned true")
        } else {
                fmt.Fprintln(rw, "URL Returned False")
        }

}
