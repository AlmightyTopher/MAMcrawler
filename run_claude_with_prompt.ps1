while ($true) {

    # Start Claude (replace this with your actual command)
    claude --dangerously-skip-permissions

    Write-Host -NoNewline "Would you like it to resume? Y/N: "
    $answer = Read-Host

    switch ($answer.ToUpper()) {
        "Y" {
            claude --dangerously-skip-permissions | Out-Null
            Write-Host "Sent: resume"
            "resume" | claude --dangerously-skip-permissions
        }
        "N" {
            Write-Host "Not resuming. Exiting."
            exit
        }
        default {
            Write-Host "Invalid input. Exiting."
            exit
        }
    }
}
