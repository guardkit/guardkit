richardwoollcott@Mac guardkit % pytest tests/unit/knowledge/ tests/integration/graphiti/ tests/cli/test_graphiti*.py \
  -v -m "not live" --tb=short
======================================== test session starts ========================================
platform darwin -- Python 3.14.2, pytest-8.4.2, pluggy-1.6.0 -- /opt/homebrew/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Users/richardwoollcott/Projects/appmilla_github/guardkit
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 202 items / 5 deselected / 197 selected

tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_valid_feature_id_simple PASSED [  0%]
tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_valid_feature_id_complex PASSED [  1%]
tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_feature_id_with_alphanumeric_prefix PASSED [  1%]
tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_feature_id_returns_none_when_no_pattern PASSED [  2%]
tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_feature_id_returns_none_for_empty_string PASSED [  2%]
tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_feature_id_case_sensitive PASSED [  3%]
tests/unit/knowledge/test_feature_detector.py::TestDetectFeatureId::test_detect_feature_id_first_match_when_multiple PASSED [  3%]
tests/unit/knowledge/test_feature_detector.py::TestFindFeatureSpec::test_find_feature_spec_in_docs_features PASSED [  4%]
tests/unit/knowledge/test_feature_detector.py::TestFindFeatureSpec::test_find_feature_spec_in_guardkit_features PASSED [  4%]
tests/unit/knowledge/test_feature_detector.py::TestFindFeatureSpec::test_find_feature_spec_in_features_root PASSED [  5%]
tests/unit/knowledge/test_feature_detector.py::TestFindFeatureSpec::test_find_feature_spec_returns_none_when_not_found PASSED [  5%]
tests/unit/knowledge/test_feature_detector.py::TestFindFeatureSpec::test_find_feature_spec_with_missing_directories PASSED [  6%]
tests/unit/knowledge/test_feature_detector.py::TestFindRelatedFeatures::test_find_related_features_same_prefix PASSED [  6%]
tests/unit/knowledge/test_feature_detector.py::TestFindRelatedFeatures::test_find_related_features_excludes_self PASSED [  7%]
tests/unit/knowledge/test_feature_detector.py::TestFindRelatedFeatures::test_find_related_features_different_prefix_excluded PASSED [  7%]
tests/unit/knowledge/test_feature_detector.py::TestFindRelatedFeatures::test_find_related_features_returns_empty_when_none PASSED [  8%]
tests/unit/knowledge/test_feature_detector.py::TestFindRelatedFeatures::test_find_related_features_invalid_feature_id PASSED [  8%]
tests/unit/knowledge/test_feature_detector.py::TestEdgeCases::test_detector_with_none_project_root PASSED [  9%]
tests/unit/knowledge/test_feature_detector.py::TestEdgeCases::test_find_feature_spec_with_partial_match PASSED [  9%]
tests/unit/knowledge/test_feature_detector.py::TestEdgeCases::test_default_feature_paths_exist PASSED [ 10%]
tests/unit/knowledge/test_feature_detector.py::TestFeatureIdPattern::test_feature_id_pattern_exists PASSED [ 10%]
tests/unit/knowledge/test_feature_detector.py::TestFeatureIdPattern::test_feature_id_pattern_matches_valid_formats PASSED [ 11%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestFeaturePlanContextBuilderInitialization::test_constructor_accepts_project_root_path PASSED [ 11%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestFeaturePlanContextBuilderInitialization::test_constructor_handles_none_project_root PASSED [ 12%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestFeaturePlanContextBuilderInitialization::test_constructor_initializes_dependencies PASSED [ 12%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestBuildContextBasic::test_returns_feature_plan_context_instance PASSED [ 13%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestBuildContextBasic::test_with_description_containing_feature_id PASSED [ 13%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestBuildContextBasic::test_with_explicit_context_files_parameter PASSED [ 14%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestBuildContextBasic::test_with_tech_stack_parameter PASSED [ 14%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestFeatureDetectionIntegration::test_auto_detects_feature_id_from_description PASSED [ 15%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestFeatureDetectionIntegration::test_finds_feature_spec_file_when_feature_id_detected PASSED [ 15%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestFeatureDetectionIntegration::test_handles_no_feature_id_gracefully PASSED [ 16%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGraphitiQueries::test_queries_related_features_group PASSED [ 16%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGraphitiQueries::test_queries_patterns_tech_stack_group PASSED [ 17%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGraphitiQueries::test_queries_failure_patterns_group PASSED [ 17%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGraphitiQueries::test_queries_role_constraints_group PASSED [ 18%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGraphitiQueries::test_queries_quality_gate_configs_group PASSED [ 18%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGraphitiQueries::test_queries_implementation_modes_group PASSED [ 19%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGracefulDegradation::test_handles_graphiti_disabled PASSED [ 19%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGracefulDegradation::test_handles_graphiti_query_failures_gracefully PASSED [ 20%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestGracefulDegradation::test_returns_valid_context_even_when_all_queries_fail PASSED [ 20%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestIntegration::test_full_flow_with_all_components PASSED [ 21%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestIntegration::test_context_includes_all_expected_fields PASSED [ 21%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestEdgeCases::test_empty_description PASSED [ 22%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestEdgeCases::test_empty_tech_stack PASSED [ 22%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestEdgeCases::test_none_context_files PASSED [ 23%]
tests/unit/knowledge/test_feature_plan_context_builder.py::TestEdgeCases::test_nonexistent_context_files PASSED [ 23%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeCreation::test_upsert_creates_when_not_exists PASSED [ 24%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeCreation::test_upsert_returns_created_action PASSED [ 24%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeSkip::test_upsert_skips_when_exact_match PASSED [ 25%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeSkip::test_upsert_returns_skipped_action PASSED [ 25%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeUpdate::test_upsert_updates_when_exists_different_content PASSED [ 26%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeUpdate::test_upsert_returns_updated_action PASSED [ 26%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeTimestamps::test_upsert_preserves_created_at_on_update PASSED [ 27%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeTimestamps::test_upsert_updates_updated_at_on_update PASSED [ 27%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeGracefulDegradation::test_upsert_returns_none_when_disabled PASSED [ 28%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeGracefulDegradation::test_upsert_returns_none_when_not_initialized PASSED [ 28%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeSourceHash::test_upsert_generates_source_hash_from_content PASSED [ 29%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeSourceHash::test_upsert_uses_provided_source_hash PASSED [ 29%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeEntityId::test_upsert_passes_entity_id_to_episode_exists PASSED [ 30%]
tests/unit/knowledge/test_upsert_episode.py::TestUpsertEpisodeEntityId::test_upsert_includes_entity_id_in_metadata PASSED [ 30%]
tests/integration/graphiti/test_clear_integration.py::TestClearAllIntegration::test_clear_all_removes_seeding_marker PASSED [ 31%]
tests/integration/graphiti/test_clear_integration.py::TestClearAllIntegration::test_clear_all_calls_client_clear_all PASSED [ 31%]
tests/integration/graphiti/test_clear_integration.py::TestClearAllIntegration::test_clear_all_shows_preview_before_clearing PASSED [ 32%]
tests/integration/graphiti/test_clear_integration.py::TestClearSystemOnlyIntegration::test_clear_system_only_calls_correct_method PASSED [ 32%]
tests/integration/graphiti/test_clear_integration.py::TestClearSystemOnlyIntegration::test_clear_system_only_preview_shows_only_system PASSED [ 33%]
tests/integration/graphiti/test_clear_integration.py::TestClearProjectOnlyIntegration::test_clear_project_only_calls_correct_method PASSED [ 34%]
tests/integration/graphiti/test_clear_integration.py::TestClearProjectOnlyIntegration::test_clear_project_only_preview_shows_only_project PASSED [ 34%]
tests/integration/graphiti/test_clear_integration.py::TestClearDryRunIntegration::test_dry_run_does_not_clear_data PASSED [ 35%]
tests/integration/graphiti/test_clear_integration.py::TestClearDryRunIntegration::test_dry_run_with_system_only PASSED [ 35%]
tests/integration/graphiti/test_clear_integration.py::TestClearIdempotency::test_clear_twice_is_safe PASSED [ 36%]
tests/integration/graphiti/test_clear_integration.py::TestClearErrorRecovery::test_clear_partial_failure_returns_result PASSED [ 36%]
tests/integration/graphiti/test_multi_project_namespace.py::TestMultiProjectIsolation::test_separate_project_knowledge_groups SKIPPED [ 37%]
tests/integration/graphiti/test_multi_project_namespace.py::TestMultiProjectIsolation::test_project_a_cannot_see_project_b_knowledge SKIPPED [ 37%]
tests/integration/graphiti/test_multi_project_namespace.py::TestMultiProjectIsolation::test_project_b_cannot_see_project_a_knowledge SKIPPED [ 38%]
tests/integration/graphiti/test_multi_project_namespace.py::TestMultiProjectIsolation::test_same_group_name_different_namespace SKIPPED [ 38%]
tests/integration/graphiti/test_multi_project_namespace.py::TestSystemKnowledgeSharing::test_system_groups_are_shared SKIPPED [ 39%]
tests/integration/graphiti/test_multi_project_namespace.py::TestSystemKnowledgeSharing::test_guardkit_prefix_is_always_system SKIPPED [ 39%]
tests/integration/graphiti/test_multi_project_namespace.py::TestCrossProjectSearch::test_explicit_cross_project_search SKIPPED [ 40%]
tests/integration/graphiti/test_multi_project_namespace.py::TestCrossProjectSearch::test_global_search_across_all_projects SKIPPED [ 40%]
tests/integration/graphiti/test_multi_project_namespace.py::TestConfigurationMethods::test_yaml_config_project_id PASSED [ 41%]
tests/integration/graphiti/test_multi_project_namespace.py::TestConfigurationMethods::test_env_var_override_project_id PASSED [ 41%]
tests/integration/graphiti/test_multi_project_namespace.py::TestConfigurationMethods::test_auto_detect_from_directory PASSED [ 42%]
tests/integration/graphiti/test_multi_project_namespace.py::TestEdgeCases::test_project_id_validation_invalid_characters PASSED [ 42%]
tests/integration/graphiti/test_multi_project_namespace.py::TestEdgeCases::test_project_id_validation_too_long PASSED [ 43%]
tests/integration/graphiti/test_multi_project_namespace.py::TestEdgeCases::test_project_id_validation_max_length_accepted PASSED [ 43%]
tests/integration/graphiti/test_multi_project_namespace.py::TestEdgeCases::test_add_episode_without_project_id_fails PASSED [ 44%]
tests/integration/graphiti/test_multi_project_namespace.py::TestPerformance::test_prefixing_overhead_is_minimal SKIPPED [ 44%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingIntegrationWithMetadata::test_seeding_adds_metadata_to_all_episodes PASSED [ 45%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingIntegrationWithMetadata::test_seeding_creates_marker_file_with_metadata PASSED [ 45%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingIntegrationWithMetadata::test_force_reseeding_updates_metadata_timestamps PASSED [ 46%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingIntegrationWithMetadata::test_seeding_skipped_if_already_seeded PASSED [ 46%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingErrorHandlingIntegration::test_seeding_continues_on_partial_failures PASSED [ 47%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingErrorHandlingIntegration::test_seeding_handles_disabled_client PASSED [ 47%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingErrorHandlingIntegration::test_seeding_handles_none_client PASSED [ 48%]
tests/integration/graphiti/test_seeding_integration.py::TestMetadataVersionTracking::test_metadata_version_matches_seeding_version PASSED [ 48%]
tests/integration/graphiti/test_seeding_integration.py::TestMetadataVersionTracking::test_marker_file_timestamp_is_recent PASSED [ 49%]
tests/integration/graphiti/test_seeding_integration.py::TestSeedingCategoriesIntegration::test_all_categories_include_metadata PASSED [ 49%]
tests/integration/graphiti/test_workflow_integration.py::TestSeedingWorkflow::test_seed_creates_metadata_episodes PASSED [ 50%]
tests/integration/graphiti/test_workflow_integration.py::TestSeedingWorkflow::test_seed_creates_marker_with_version PASSED [ 50%]
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_load_critical_context_structure PASSED [ 51%]
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_load_context_graceful_degradation PASSED [ 51%]
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_load_context_handles_disabled_client PASSED [ 52%]
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_load_context_for_feature_build_includes_extra PASSED [ 52%]
tests/integration/graphiti/test_workflow_integration.py::TestCLICommandIntegration::test_graphiti_status_command PASSED [ 53%]
tests/integration/graphiti/test_workflow_integration.py::TestCLICommandIntegration::test_graphiti_verify_command_runs_queries PASSED [ 53%]
tests/integration/graphiti/test_workflow_integration.py::TestGracefulDegradation::test_context_loading_without_graphiti PASSED [ 54%]
tests/integration/graphiti/test_workflow_integration.py::TestGracefulDegradation::test_search_returns_empty_on_error PASSED [ 54%]
tests/integration/graphiti/test_workflow_integration.py::TestGracefulDegradation::test_disabled_client_skips_operations PASSED [ 55%]
tests/integration/graphiti/test_workflow_integration.py::TestWorkflowSequence::test_task_work_context_injection_sequence PASSED [ 55%]
tests/integration/graphiti/test_workflow_integration.py::TestClearAndReseed::test_clear_marker_allows_reseed PASSED [ 56%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_command_exists PASSED [ 56%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_requires_interactive_flag PASSED [ 57%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_with_interactive_flag PASSED [ 57%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_with_focus_option PASSED [ 58%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_with_max_questions_option PASSED [ 58%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_supports_all_focus_areas PASSED [ 59%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_handles_disabled_graphiti PASSED [ 59%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_handles_connection_error PASSED [ 60%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_handles_session_error PASSED [ 60%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_shows_success_message PASSED [ 61%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureCommand::test_capture_shows_no_knowledge_message PASSED [ 61%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureUICallback::test_ui_callback_handles_all_events PASSED [ 62%]
tests/cli/test_graphiti_capture.py::TestGraphitiCaptureIntegration::test_capture_full_workflow PASSED [ 62%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearCommandExists::test_clear_command_exists PASSED [ 63%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearCommandExists::test_clear_shows_options PASSED [ 63%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearRequiresConfirm::test_clear_without_confirm_fails PASSED [ 64%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearRequiresConfirm::test_clear_with_confirm_proceeds PASSED [ 64%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearAll::test_clear_all_with_confirm PASSED    [ 65%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearSystemOnly::test_clear_system_only PASSED  [ 65%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearProjectOnly::test_clear_project_only PASSED [ 66%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearDryRun::test_dry_run_shows_what_would_be_deleted PASSED [ 67%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearDryRun::test_dry_run_with_system_only PASSED [ 67%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearErrorHandling::test_clear_handles_disabled_client PASSED [ 68%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearErrorHandling::test_clear_handles_connection_error PASSED [ 68%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearErrorHandling::test_clear_handles_clear_error PASSED [ 69%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearForceFlag::test_force_skips_confirmation_prompt PASSED [ 69%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearOutput::test_clear_shows_summary_before_proceeding PASSED [ 70%]
tests/cli/test_graphiti_clear.py::TestGraphitiClearMutualExclusivity::test_system_and_project_only_are_exclusive PASSED [ 70%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_command_exists PASSED     [ 71%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_features PASSED           [ 71%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_adrs PASSED               [ 72%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_patterns PASSED           [ 72%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_constraints PASSED        [ 73%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_all PASSED                [ 73%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_empty_category PASSED     [ 74%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_handles_disabled_graphiti PASSED [ 74%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_handles_connection_error PASSED [ 75%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_handles_search_error PASSED [ 75%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_handles_malformed_json PASSED [ 76%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_shows_count PASSED        [ 76%]
tests/cli/test_graphiti_list.py::TestGraphitiListCommand::test_list_invalid_category PASSED   [ 77%]
tests/cli/test_graphiti_search.py::TestSearchCommandRegistration::test_search_command_exists PASSED [ 77%]
tests/cli/test_graphiti_search.py::TestSearchCommandRegistration::test_search_requires_query_argument PASSED [ 78%]
tests/cli/test_graphiti_search.py::TestSearchCommandRegistration::test_search_help_shows_options PASSED [ 78%]
tests/cli/test_graphiti_search.py::TestSearchAllGroups::test_search_all_groups_with_results PASSED [ 79%]
tests/cli/test_graphiti_search.py::TestSearchAllGroups::test_search_all_groups_no_results PASSED [ 79%]
tests/cli/test_graphiti_search.py::TestSearchWithGroupOption::test_search_with_group_option PASSED [ 80%]
tests/cli/test_graphiti_search.py::TestSearchWithGroupOption::test_search_with_g_short_option PASSED [ 80%]
tests/cli/test_graphiti_search.py::TestSearchWithLimitOption::test_search_with_limit_option PASSED [ 81%]
tests/cli/test_graphiti_search.py::TestSearchWithLimitOption::test_search_with_n_short_option PASSED [ 81%]
tests/cli/test_graphiti_search.py::TestSearchWithLimitOption::test_search_default_limit_is_10 PASSED [ 82%]
tests/cli/test_graphiti_search.py::TestSearchOutputFormatting::test_search_shows_relevance_score PASSED [ 82%]
tests/cli/test_graphiti_search.py::TestSearchOutputFormatting::test_search_truncates_long_facts PASSED [ 83%]
tests/cli/test_graphiti_search.py::TestSearchOutputFormatting::test_search_shows_numbered_results PASSED [ 83%]
tests/cli/test_graphiti_search.py::TestSearchErrorHandling::test_search_handles_disabled_graphiti PASSED [ 84%]
tests/cli/test_graphiti_search.py::TestSearchErrorHandling::test_search_handles_connection_error PASSED [ 84%]
tests/cli/test_graphiti_search.py::TestSearchErrorHandling::test_search_handles_search_error PASSED [ 85%]
tests/cli/test_graphiti_search.py::TestSearchIntegration::test_search_with_group_and_limit PASSED [ 85%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_command_exists PASSED     [ 86%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_command_requires_knowledge_id PASSED [ 86%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_feature_spec_displays_details PASSED [ 87%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_adr_displays_details PASSED [ 87%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_project_overview_displays_details PASSED [ 88%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_pattern_displays_details PASSED [ 88%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_constraint_displays_details PASSED [ 89%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_guide_displays_details PASSED [ 89%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_not_found_displays_error PASSED [ 90%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_handles_disabled_graphiti PASSED [ 90%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_handles_connection_error PASSED [ 91%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_uses_correct_group_ids_for_feature PASSED [ 91%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_uses_correct_group_ids_for_adr PASSED [ 92%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_uses_correct_group_ids_for_project_overview PASSED [ 92%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_displays_formatted_output PASSED [ 93%]
tests/cli/test_graphiti_show.py::TestGraphitiShowCommand::test_show_help_output PASSED        [ 93%]
tests/cli/test_graphiti.py::TestGraphitiSeedCommand::test_seed_command_exists PASSED          [ 94%]
tests/cli/test_graphiti.py::TestGraphitiSeedCommand::test_seed_runs_seeding_functions PASSED  [ 94%]
tests/cli/test_graphiti.py::TestGraphitiSeedCommand::test_seed_with_force_flag PASSED         [ 95%]
tests/cli/test_graphiti.py::TestGraphitiSeedCommand::test_seed_handles_disabled_client PASSED [ 95%]
tests/cli/test_graphiti.py::TestGraphitiSeedCommand::test_seed_handles_connection_error PASSED [ 96%]
tests/cli/test_graphiti.py::TestGraphitiStatusCommand::test_status_command_exists PASSED      [ 96%]
tests/cli/test_graphiti.py::TestGraphitiStatusCommand::test_status_shows_seeding_state FAILED [ 97%]
tests/cli/test_graphiti.py::TestGraphitiVerifyCommand::test_verify_command_exists PASSED      [ 97%]
tests/cli/test_graphiti.py::TestGraphitiVerifyCommand::test_verify_runs_test_queries PASSED   [ 98%]
tests/cli/test_graphiti.py::TestGraphitiVerifyCommand::test_verify_requires_seeding PASSED    [ 98%]
tests/cli/test_graphiti.py::TestGraphitiGroupCommands::test_graphiti_group_exists PASSED      [ 99%]
tests/cli/test_graphiti.py::TestGraphitiGroupCommands::test_graphiti_shows_subcommands PASSED [100%]

============================================= FAILURES ==============================================
_____________________ TestGraphitiStatusCommand.test_status_shows_seeding_state _____________________
tests/cli/test_graphiti.py:140: in test_status_shows_seeding_state
    assert "seeded" in result.output.lower()
E   assert 'seeded' in "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       graphiti knowledge status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  status: enabled\n\n  system knowledge:\n  error: 'magicmock' object can't be awaited\n\n"
E    +  where "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       graphiti knowledge status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  status: enabled\n\n  system knowledge:\n  error: 'magicmock' object can't be awaited\n\n" = <built-in method lower of str object at 0x13d19d640>()
E    +    where <built-in method lower of str object at 0x13d19d640> = "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       Graphiti Knowledge Status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  Status: ENABLED\n\n  System Knowledge:\n  Error: 'MagicMock' object can't be awaited\n\n".lower
E    +      where "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       Graphiti Knowledge Status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  Status: ENABLED\n\n  System Knowledge:\n  Error: 'MagicMock' object can't be awaited\n\n" = <Result okay>.output
========================================== tests coverage ===========================================
_________________________ coverage: platform darwin, python 3.14.2-final-0 __________________________

Name                                                                            Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------------------------------------------------------------------
installer/core/lib/__init__.py                                                      0      0      0      0   100%
installer/core/lib/agent_bridge/__init__.py                                         4      4      0      0     0%   8-25
installer/core/lib/agent_bridge/invoker.py                                         79     79     20      0     0%   8-354
installer/core/lib/agent_bridge/state_manager.py                                   55     55      8      0     0%   8-235
installer/core/lib/agent_enhancement/__init__.py                                    0      0      0      0   100%
installer/core/lib/agent_enhancement/applier.py                                   326    326    154      0     0%   10-1088
installer/core/lib/agent_enhancement/boundary_utils.py                            137    137     88      0     0%   14-526
installer/core/lib/agent_enhancement/enhancer.py                                  327    327    116      0     0%   10-803
installer/core/lib/agent_enhancement/metadata_validator.py                         69     69     34      0     0%   10-264
installer/core/lib/agent_enhancement/models.py                                     47     47      4      0     0%   9-170
installer/core/lib/agent_enhancement/orchestrator.py                              121    121     46      0     0%   14-416
installer/core/lib/agent_enhancement/parser.py                                     83     83     30      0     0%   9-267
installer/core/lib/agent_enhancement/prompt_builder.py                             18     18      4      0     0%   9-198
installer/core/lib/agent_formatting/__init__.py                                     6      6      0      0     0%   7-30
installer/core/lib/agent_formatting/metrics.py                                     76     76     26      0     0%   7-281
installer/core/lib/agent_formatting/parser.py                                      87     87     32      0     0%   7-223
installer/core/lib/agent_formatting/reporter.py                                    91     91     28      0     0%   7-254
installer/core/lib/agent_formatting/transformers.py                               107    107     50      0     0%   7-295
installer/core/lib/agent_formatting/validator.py                                   48     48     18      0     0%   7-154
installer/core/lib/agent_generator/__init__.py                                      2      2      0      0     0%   12-20
installer/core/lib/agent_generator/agent_generator.py                             233    233     66      0     0%   8-742
installer/core/lib/agent_generator/agent_splitter.py                              101    101     54      0     0%   12-266
installer/core/lib/agent_generator/markdown_formatter.py                           12     12      0      0     0%   11-80
installer/core/lib/agent_orchestration/__init__.py                                  2      2      0      0     0%   21-28
installer/core/lib/agent_orchestration/agent_orchestration.py                     108    108     26      0     0%   16-325
installer/core/lib/agent_orchestration/external_discovery.py                       16     16      0      0     0%   11-86
installer/core/lib/agent_scanner/__init__.py                                        2      2      0      0     0%   14-21
installer/core/lib/agent_scanner/agent_scanner.py                                  91     91     38      0     0%   10-289
installer/core/lib/codebase_analyzer/__init__.py                                    5      5      0      0     0%   32-63
installer/core/lib/codebase_analyzer/agent_invoker.py                             251    251    130      0     0%   14-780
installer/core/lib/codebase_analyzer/ai_analyzer.py                               129    129     30      0     0%   15-430
installer/core/lib/codebase_analyzer/exclusions.py                                 37     37     24      0     0%   3-142
installer/core/lib/codebase_analyzer/models.py                                    130    130     30      0     0%   14-290
installer/core/lib/codebase_analyzer/prompt_builder.py                            138    138     60      0     0%   13-672
installer/core/lib/codebase_analyzer/response_parser.py                           113    113     30      0     0%   13-376
installer/core/lib/codebase_analyzer/serializer.py                                 91     91     22      0     0%   13-293
installer/core/lib/codebase_analyzer/stratified_sampler.py                        295    295    128      0     0%   16-839
installer/core/lib/config/__init__.py                                               4      4      0      0     0%   2-6
installer/core/lib/config/config_schema.py                                         58     58      8      0     0%   2-117
installer/core/lib/config/defaults.py                                               2      2      0      0     0%   2-5
installer/core/lib/config/plan_review_config.py                                   120    120     50      0     0%   2-297
installer/core/lib/constants.py                                                    10     10      0      0     0%   3-26
installer/core/lib/external_id_mapper.py                                          106    106     48      0     0%   33-413
installer/core/lib/external_id_persistence.py                                     145    145     60      0     0%   33-448
installer/core/lib/feature_detection.py                                            86     86     26      0     0%   51-310
installer/core/lib/guidance_generator/__init__.py                                   5      5      0      0     0%   10-15
installer/core/lib/guidance_generator/extractor.py                                 43     43     26      0     0%   8-137
installer/core/lib/guidance_generator/generator.py                                 67     67     12      0     0%   7-155
installer/core/lib/guidance_generator/path_patterns.py                             31     31     22      0     0%   15-121
installer/core/lib/guidance_generator/validator.py                                  8      8      4      0     0%   8-27
installer/core/lib/guide_generator.py                                              96     96     18      0     0%   17-535
installer/core/lib/id_generator.py                                                136    136     66      0     0%   87-827
installer/core/lib/implement_orchestrator.py                                      296    296     68      0     0%   35-741
installer/core/lib/implementation_mode_analyzer.py                                 68     68     28      0     0%   30-300
installer/core/lib/mcp/__init__.py                                                  5      5      0      0     0%   19-24
installer/core/lib/mcp/context7_client.py                                          61     61     24      0     0%   22-315
installer/core/lib/mcp/detail_level.py                                             19     19      4      0     0%   12-87
installer/core/lib/mcp/monitor.py                                                 110    110     28      0     0%   31-465
installer/core/lib/mcp/utils.py                                                    29     29     16      0     0%   12-139
installer/core/lib/metrics/__init__.py                                              3      3      0      0     0%   2-5
installer/core/lib/metrics/metrics_storage.py                                      80     80     24      0     0%   2-164
installer/core/lib/metrics/plan_review_dashboard.py                               133    133     52      0     0%   2-264
installer/core/lib/metrics/plan_review_metrics.py                                  33     33      8      0     0%   2-197
installer/core/lib/orchestrator/__init__.py                                         2      0      0      0   100%
installer/core/lib/orchestrator/worktrees.py                                      124     93     18      0    22%   102, 135-142, 187-192, 201-204, 227-239, 258, 273-274, 296, 310-314, 326-330, 339-343, 374-437, 466-492, 521-536, 566
installer/core/lib/orchestrator_error_messages.py                                  56     56     16      0     0%   16-272
installer/core/lib/parallel_analyzer.py                                           104    104     58      0     0%   28-397
installer/core/lib/pattern_generator.py                                           159    159     80      0     0%   10-482
installer/core/lib/readme_generator.py                                            106    106     38      0     0%   28-358
installer/core/lib/review_parser.py                                               145    145     60      0     0%   38-452
installer/core/lib/rules_generator/__init__.py                                      2      2      0      0     0%   3-5
installer/core/lib/rules_generator/code_style.py                                   18     18      0      0     0%   3-240
installer/core/lib/rules_generator/generator.py                                    40     40     12      0     0%   3-96
installer/core/lib/rules_generator/patterns.py                                     19     19      0      0     0%   3-355
installer/core/lib/rules_generator/testing.py                                      19     19      0      0     0%   3-500
installer/core/lib/settings_generator/__init__.py                                   5      5      0      0     0%   7-42
installer/core/lib/settings_generator/generator.py                                178    178    100      0     0%   7-525
installer/core/lib/settings_generator/models.py                                    57     57      0      0     0%   11-167
installer/core/lib/settings_generator/tests/__init__.py                             0      0      0      0   100%
installer/core/lib/settings_generator/tests/test_generator.py                     160    160      6      0     0%   7-313
installer/core/lib/settings_generator/validator.py                                 91     91     68      0     0%   7-250
installer/core/lib/state_paths.py                                                  19     19      0      0     0%   10-100
installer/core/lib/stub_detector.py                                                52     52     30      0     0%   31-387
installer/core/lib/task_review/__init__.py                                          2      2      0      0     0%   3-5
installer/core/lib/task_review/model_router.py                                     48     48     16      0     0%   14-202
installer/core/lib/template_config_handler.py                                     121    121     70      0     0%   10-404
installer/core/lib/template_creation/__init__.py                                    3      3      0      0     0%   8-15
installer/core/lib/template_creation/constants.py                                  12     12      0      0     0%   11-51
installer/core/lib/template_creation/manifest_generator.py                        220    220     92      0     0%   9-575
installer/core/lib/template_creation/models.py                                     42     42      0      0     0%   8-119
installer/core/lib/template_generator/__init__.py                                   8      8      0      0     0%   34-79
installer/core/lib/template_generator/ai_client.py                                 45     45     14      0     0%   8-263
installer/core/lib/template_generator/claude_md_generator.py                      519    519    256      0     0%   9-1561
installer/core/lib/template_generator/completeness_validator.py                   184    184     76      0     0%   11-678
installer/core/lib/template_generator/extended_validator.py                       222    222    106      0     0%   10-678
installer/core/lib/template_generator/layer_classifier.py                         197    197    114      0     0%   19-936
installer/core/lib/template_generator/models.py                                   142    142      4      0     0%   8-447
installer/core/lib/template_generator/path_pattern_inferrer.py                     72     72     32      0     0%   9-261
installer/core/lib/template_generator/path_resolver.py                            113    113     38      0     0%   19-443
installer/core/lib/template_generator/pattern_matcher.py                          126    126     80      0     0%   10-427
installer/core/lib/template_generator/placeholder_patterns.py                      95     95     34      0     0%   11-330
installer/core/lib/template_generator/report_generator.py                          79     79     44      0     0%   9-296
installer/core/lib/template_generator/rules_structure_generator.py                313    313    112      0     0%   14-948
installer/core/lib/template_generator/template_generator.py                       245    245    128      0     0%   10-683
installer/core/lib/template_generator/tests/__init__.py                             0      0      0      0   100%
installer/core/lib/template_generator/tests/test_placeholder_patterns.py          162    162      2      0     0%   7-350
installer/core/lib/template_generator/tests/test_rules_generator.py               279    279      2      0     0%   7-778
installer/core/lib/template_qa_orchestrator.py                                    157    157     22      0     0%   10-383
installer/core/lib/template_validation/__init__.py                                  7      7      0      0     0%   7-25
installer/core/lib/template_validation/ai_analysis_helpers.py                     127    127     82      0     0%   8-396
installer/core/lib/template_validation/ai_service.py                               63     63     14      0     0%   8-285
installer/core/lib/template_validation/audit_report_generator.py                  188    188     90      0     0%   7-433
installer/core/lib/template_validation/audit_session.py                            59     59     10      0     0%   7-131
installer/core/lib/template_validation/comprehensive_auditor.py                    41     41      4      0     0%   7-140
installer/core/lib/template_validation/models.py                                   81     81      0      0     0%   7-240
installer/core/lib/template_validation/orchestrator.py                            191    191     60      0     0%   7-329
installer/core/lib/template_validation/progressive_disclosure_validator.py        136    136     48      0     0%   7-351
installer/core/lib/template_validation/sections/__init__.py                        17     17      0      0     0%   7-24
installer/core/lib/template_validation/sections/section_01_manifest.py            157    157     60      0     0%   7-419
installer/core/lib/template_validation/sections/section_02_settings.py             38     38      6      0     0%   7-118
installer/core/lib/template_validation/sections/section_03_documentation.py        49     49     16      0     0%   8-145
installer/core/lib/template_validation/sections/section_04_files.py                32     32      6      0     0%   7-92
installer/core/lib/template_validation/sections/section_05_agents.py               46     46     12      0     0%   8-95
installer/core/lib/template_validation/sections/section_06_readme.py               28     28      4      0     0%   7-60
installer/core/lib/template_validation/sections/section_07_global.py               26     26      6      0     0%   7-53
installer/core/lib/template_validation/sections/section_08_comparison.py           98     98     28      0     0%   7-397
installer/core/lib/template_validation/sections/section_09_production.py           18     18      0      0     0%   7-39
installer/core/lib/template_validation/sections/section_10_scoring.py              18     18      0      0     0%   7-39
installer/core/lib/template_validation/sections/section_11_findings.py            125    125     30      0     0%   7-602
installer/core/lib/template_validation/sections/section_12_testing.py              59     59     14      0     0%   7-231
installer/core/lib/template_validation/sections/section_13_market.py               18     18      0      0     0%   7-40
installer/core/lib/template_validation/sections/section_14_recommendations.py      18     18      0      0     0%   7-40
installer/core/lib/template_validation/sections/section_15_testing_recs.py         18     18      0      0     0%   7-40
installer/core/lib/template_validation/sections/section_16_summary.py              18     18      0      0     0%   7-39
installer/core/lib/utils/__init__.py                                                5      5      0      0     0%   2-7
installer/core/lib/utils/feature_utils.py                                          22     22     12      0     0%   2-70
installer/core/lib/utils/file_io.py                                                48     48      0      0     0%   23-130
installer/core/lib/utils/file_operations.py                                        51     51      2      0     0%   2-117
installer/core/lib/utils/json_serializer.py                                        36     36      2      0     0%   2-97
installer/core/lib/utils/path_resolver.py                                          28     28      6      0     0%   2-81
---------------------------------------------------------------------------------------------------------------------------
TOTAL                                                                           11819  11786   4128      0     1%
Coverage JSON written to file coverage.json
====================================== short test summary info ======================================
FAILED tests/cli/test_graphiti.py::TestGraphitiStatusCommand::test_status_shows_seeding_state - assert 'seeded' in "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       graphiti knowledge status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  status: enabled\n\n  system knowledge:\n  error: 'magicmock' object can't be awaited\n\n"
 +  where "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       graphiti knowledge status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  status: enabled\n\n  system knowledge:\n  error: 'magicmock' object can't be awaited\n\n" = <built-in method lower of str object at 0x13d19d640>()
 +    where <built-in method lower of str object at 0x13d19d640> = "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       Graphiti Knowledge Status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  Status: ENABLED\n\n  System Knowledge:\n  Error: 'MagicMock' object can't be awaited\n\n".lower
 +      where "\n\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n\u2551       Graphiti Knowledge Status        \u2551\n\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n\n  Status: ENABLED\n\n  System Knowledge:\n  Error: 'MagicMock' object can't be awaited\n\n" = <Result okay>.output
====================== 1 failed, 187 passed, 9 skipped, 5 deselected in 2.70s =======================
richardwoollcott@Mac guardkit %