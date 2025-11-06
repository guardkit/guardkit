using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace MauiSample.ViewModels;

public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    private string title = "MAUI Sample";

    [RelayCommand]
    private void DoSomething()
    {
        Title = "Button Clicked!";
    }
}
