# Development Notes

Python version 3.11.2

## Heroku git Deployment

Since Heroku (for the forseeable future) no longer supports github automated
deployments the code must be deployed manually via git.

This can be accomplished as documented here:

```bash
heroku login
get remote -v
git push stage-grc main
```

## Email Handling

For email handling to work when running locally you need to run a local SMTP
server.  This is accomplished using the nullsmtpd package.  The package is
already part of the requirements so should already be present.

Launch the process using the following command:

```bash
nullsmtpd --no-fork --mail-dir .mail
```

The command-line paramters used do the following:

- `--no-fork`: causes the process to run in the bash/terminal/cmd window
- `--mail-dir .mail`: causes all email to be saved to the folder `.mail/{to address}/`

### Testing

https://docs.google.com/document/d/1Y1lNFpbdy4DKtXPpaTskgELkfr1ZmxNUX7AnBEh_MpU/edit?usp=sharing


## Charting

### Paid

https://www.fusioncharts.com/ - SELECTED
When we upgrade FusionCharts, we are having an issues with this error:
The file 'assets/js/fusioncharts/themes/fusioncharts.theme.zune.js.map' could not be found with <whitenoise.storage.CompressedManifestStaticFilesStorage object at 0x7fc035cf89d0>.
The solution was to go through each assets/js/fusioncharts/themes/*.js file and remove //# sourceMappingURL=.....js.map from the end of it.

### Free (all suck)

https://www.chartjs.org/

https://github.com/ciprianciurea/chartjs-plugin-doughnutlabel

https://www.npmjs.com/package/chartjs-plugin-piechart-outlabels

https://github.com/Neckster/chartjs-plugin-piechart-outlabels/issues/23#issuecomment-948420072
